import requests, requests_cache
from retry_requests import retry
import sqlite3
import datetime

from config_reader import (get_weather_settings, get_irrigation_settings, get_database_settings)

# setup client (cache + retry)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=3, backoff_factor=0.2)

def save_to_db_from_api(days) -> None:
    conn = sqlite3.connect(get_database_settings(["name"]))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precipitation (
            date TEXT PRIMARY KEY,
            is_rain BOOLEAN,
            updated_at TEXT,
            manual BOOLEAN DEFAULT FALSE
        )
    """)

    today = datetime.now().date()

    for day, is_rain in days.items():
        date_obj = datetime.fromisoformat(day).date()

        if date_obj < today:
            # passato → inserisci solo se NON esiste già
            # Qua bisogna sovrascrivere anche il passato perchè è più sicuro del futuro. Ignorando le robe manuali inserite.
            cursor.execute("""
                INSERT OR IGNORE INTO precipitation (date, is_rain, updated_at, manual)
                VALUES (?, ?, ?, FALSE)
            """, (day, is_rain, datetime.utcnow().isoformat()))
        else:
            # oggi e futuro → aggiorna sempre
            cursor.execute("""
                INSERT OR REPLACE INTO precipitation (date, is_rain, updated_at, manual)
                VALUES (?, ?, ?, FALSE)
            """, (day, is_rain, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

def update_db_from_telegram() -> None:
    """
    Aggiorna il DB impostando is_rain=True e manual=True per la data di oggi.
    Ritorna True se tutto va bene, False se c'è un errore.
    """
    conn = sqlite3.connect(get_database_settings(["name"]))

    try:
        cursor = conn.cursor()
        
        # Aggiorna la riga della data di oggi
        cursor.execute(
            "UPDATE precipitation SET is_rain = ?, manual = ?, updated_at = ? WHERE date = ?",
            (True, True, datetime.utcnow().isoformat(), datetime.now().date().isoformat())
        )
        
        conn.commit()
        
    except Exception as e:
        raise RuntimeError(f"Errore aggiornando il DB: {e}") from e
    finally:
        if conn in locals():
            conn.close()

def get_daily_precipitation() -> None:
    wtr_settings = get_weather_settings()
    irr_settings = get_irrigation_settings()

    params = {
        "latitude": wtr_settings["latitude"],
        "longitude": wtr_settings["longitude"],
        "daily": "precipitation_sum",
        "timezone": "Europe/Rome",
        "forecast_days": irr_settings["range_future_days"]+1,
        "past_days": irr_settings["range_past_days"]
    }

    response = requests.get(get_weather_settings()["url_api"], params=params)
    response.raise_for_status()  # solleva errore se la request fallisce

    data = response.json()

    dates = data["daily"]["time"]
    precipitation = data["daily"]["precipitation_sum"]

    # crea dict: { "2026-05-04": 2.3, ... }
    result = dict(zip(dates, precipitation > irr_settings["rain_threshold_mm"]))

    save_to_db_from_api(result)

def get_precipitation_from_db() -> dict:
    conn = sqlite3.connect(get_database_settings(["name"]))
    cursor = conn.cursor()

    cursor.execute("SELECT date, is_rain FROM precipitation")
    rows = cursor.fetchall()

    conn.close()

    return {row[0]: bool(row[1]) for row in rows}