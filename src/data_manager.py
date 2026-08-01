"""
Modulo per la gestione dei dati.
Gestisce l'interazione con il database SQLite e le chiamate all'API meteo.
Include funzioni per salvare, aggiornare e recuperare dati di precipitazione.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import requests_cache
from retry_requests import retry

from config_reader import get_database_settings

from telegram.ext import ContextTypes

# Logger per questo modulo
logger = logging.getLogger(__name__)
ROME_TZ = ZoneInfo("Europe/Rome")

# Setup del client HTTP con cache e retry automatico
# Cache: salva le risposte per 1 ora per evitare chiamate ripetute
# Retry: ritenta fino a 3 volte con backoff esponenziale
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=3, backoff_factor=0.2)


@dataclass
class DailyPrecipitation:
    date: str
    is_rain: bool
    rain_mm: float
    sunrise: str  # Ora dell'alba
    sunset: str  # Ora del tramonto


def save_to_db_from_api(days: list[DailyPrecipitation]) -> None:
    """
    Salva nel database i dati di precipitazione ricevuti dall'API meteo.

    La tabella precipitation memorizza per ogni data se ha piovuto o no,
    con timestamp di aggiornamento e flag per dati manuali vs automatici.

    Args:
        days: Lista di oggetti con data, flag pioggia e quantità in mm

    Raises:
        RuntimeError: Se ci sono errori nel database
    """
    db_path = get_database_settings()["name"]
    try:
        create_db_if_not_exists()  # Assicurati che la tabella esista prima di salvare

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            now_iso = datetime.now(ROME_TZ).isoformat()

            for day_data in days:
                # Aggiorna solo record automatici (non manuali) per evitare sovrascritture
                cursor.execute(
                    """
                    UPDATE precipitation
                    SET is_rain = ?, rain_mm = ?, updated_at = ?, sunrise = ?, sunset = ?
                    WHERE date = ? AND manual = FALSE
                """,
                    (
                        day_data.is_rain,
                        day_data.rain_mm,
                        now_iso,
                        day_data.sunrise,
                        day_data.sunset,
                        day_data.date,
                    ),
                )

                # Inserisce nuovo record se non esiste (non sovrascrive manuali)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO precipitation (date, is_rain, rain_mm, updated_at, manual, sunrise, sunset)
                    VALUES (?, ?, ?, ?, FALSE, ?, ?)
                """,
                    (
                        day_data.date,
                        day_data.is_rain,
                        day_data.rain_mm,
                        now_iso,
                        day_data.sunrise,
                        day_data.sunset,
                    ),
                )

            conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore nel salvataggio nel DB: {exc}") from exc


def update_db_from_telegram() -> None:
    """
    Aggiorna il database quando l'utente conferma manualmente l'irrigazione.

    Imposta is_rain=True, rain_mm=NULL e manual=True per la data odierna,
    segnalando che oggi ha piovuto (irrigazione effettuata).
    """
    db_path = get_database_settings()["name"]
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE precipitation SET is_rain = ?, rain_mm = ?, manual = ?, updated_at = ? WHERE date = ?",
                (
                    True,  # Ha piovuto (irrigato)
                    None,  # Quantità pioggia non nota per manuale
                    True,  # Modifica manuale
                    datetime.now(ROME_TZ).isoformat(),
                    datetime.now(ROME_TZ).date().isoformat(),
                ),
            )

            conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore aggiornando il DB: {exc}") from exc


def reset_today_precipitation() -> None:
    """
    Resetta i dati di precipitazione per la data odierna.

    Imposta is_rain=False, rain_mm=NULL e manual=False per la data odierna,
    segnalando che oggi non ha piovuto (reset manuale).
    """
    db_path = get_database_settings()["name"]
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE precipitation SET is_rain = ?, rain_mm = ?, manual = ?, updated_at = ? WHERE date = ?",
                (
                    False,  # Non ha piovuto
                    0.0,  # Quantità pioggia non nota
                    False,  # Non è una modifica manuale di irrigazione
                    datetime.now(ROME_TZ).isoformat(),
                    datetime.now(ROME_TZ).date().isoformat(),
                ),
            )

            conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore resettando il DB: {exc}") from exc


def get_all_precipitation_data() -> list[dict]:
    """
    Recupera tutti i dati di precipitazione dal database con dettagli completi.

    Returns:
        list[dict]: Lista di dizionari con chiavi 'date', 'is_rain', 'rain_mm', 'manual', 'updated_at'

    Raises:
        RuntimeError: Se ci sono errori nella lettura del database
    """
    db_path = get_database_settings()["name"]
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT date, is_rain, rain_mm, manual, updated_at FROM precipitation ORDER BY date"
            )
            rows = cursor.fetchall()

        return [
            {
                "date": row[0],
                "is_rain": bool(row[1]),
                "rain_mm": row[2],
                "manual": bool(row[3]),
                "updated_at": row[4],
            }
            for row in rows
        ]
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore leggendo dal DB: {exc}") from exc


def get_sunset_sunrise_for_date(date: str) -> tuple[str, str]:
    """
    Recupera l'orario di alba e tramonto per una data specifica dal database.

    Args:
        date (str): Data in formato ISO

    Returns:
        tuple[str, str]: Tupla contenente (sunrise, sunset) in formato ISO

    Raises:
        RuntimeError: Se ci sono errori nella lettura del database
    """
    db_path = get_database_settings()["name"]
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT sunrise, sunset FROM precipitation WHERE date = ?", (date,)
            )
            row = cursor.fetchone()

        if row:
            return row[0], row[1]  # (sunrise, sunset)
        else:
            return None, None  # Nessun dato trovato per la data specificata
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore leggendo alba/tramonto dal DB: {exc}") from exc


def create_db_if_not_exists() -> None:
    """
    Crea la tabella precipitation nel database se non esiste già.

    Questo è utile per assicurarsi che il database sia pronto all'uso
    prima di tentare di salvare o leggere dati.
    """
    db_path = get_database_settings()["name"]
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS precipitation (
                    date TEXT PRIMARY KEY,        -- Data in formato ISO (YYYY-MM-DD)
                    is_rain BOOLEAN,              -- True se ha piovuto quel giorno
                    rain_mm REAL,                 -- Quantità di pioggia in mm (opzionale)
                    updated_at TEXT,              -- Timestamp ultima modifica (ISO)
                    manual BOOLEAN DEFAULT FALSE,  -- True se modificato manualmente
                    sunrise TEXT,                 -- Ora dell'alba
                    sunset TEXT                  -- Ora del tramonto
                )
            """)
            conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore creando la tabella nel DB: {exc}") from exc
