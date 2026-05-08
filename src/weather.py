import requests
import requests_cache
from retry_requests import retry
import sqlite3
import datetime

from configReader import (getWeatherConfig, getWeatherConfig, getUrlAPI, getDBconfig)

# setup client (cache + retry)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=3, backoff_factor=0.2)

conn = sqlite3.connect(getDBconfig(["name"]))

def savetodb_fromApi(data):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precipitation (
            date TEXT PRIMARY KEY,
            israin BOOLEAN,
            updated_at TEXT,
            manual BOOLEAN DEFAULT FALSE
        )
    """)

    today = datetime.now().date()

    for date, value in data.items():
        date_obj = datetime.fromisoformat(date).date()

        if date_obj < today:
            # passato → inserisci solo se NON esiste già
            cursor.execute("""
                INSERT OR IGNORE INTO precipitation (date, value, updated_at, manual)
                VALUES (?, ?, ?, FALSE)
            """, (date, value, datetime.utcnow().isoformat()))
        else:
            # oggi e futuro → aggiorna sempre
            cursor.execute("""
                INSERT OR REPLACE INTO precipitation (date, value, updated_at, manual)
                VALUES (?, ?, ?, FALSE)
            """, (date, value, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

def updatedb_fromTelegram():
    """
    Aggiorna il DB impostando israin=True e manual=True per la data di oggi.
    Ritorna True se tutto va bene, False se c'è un errore.
    """
    try:
        cursor = conn.cursor()
        
        # Aggiorna la riga della data di oggi
        cursor.execute(
            "UPDATE precipitation SET israin = ?, manual = ?, updated_at = ? WHERE date = ?",
            (True, True, datetime.utcnow().isoformat(), datetime.now().date().isoformat())
        )
        
        conn.commit()
        return True
    except Exception as e:
        raise RuntimeError(f"Errore aggiornando il DB: {e}") from e
    finally:
        # Chiudi sempre la connessione
        if conn is not None:
            conn.close()

def get_daily_precipitation(days, type="forecast"):
    wtrConf = getWeatherConfig()
    irrSettings = getWateringConfig()

    params = {
        "latitude": wtrConf["latitude"],
        "longitude": wtrConf["longitude"],
        "daily": "precipitation_sum",
        "timezone": "Europe/Rome",
        "forecast_days": irrSettings["range_days" ],
        "past_days": irrSettings["range_days"]
    }

    response = requests.get(getUrlAPI(), params=params)
    response.raise_for_status()  # solleva errore se la request fallisce

    data = response.json()

    dates = data["daily"]["time"]
    precipitation = data["daily"]["precipitation_sum"]

    # crea dict: { "2026-05-04": 2.3, ... }
    result = dict(zip(dates, precipitation>wtrConf["rain_threshold_mm"]))

    savetodb_fromApi(result)

    return result
