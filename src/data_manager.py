"""
Modulo per la gestione dei dati.
Gestisce l'interazione con il database SQLite e le chiamate all'API meteo.
Include funzioni per salvare, aggiornare e recuperare dati di precipitazione.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
import requests_cache
from retry_requests import retry

from config_reader import (
    get_database_settings,
    get_irrigation_settings,
    get_weather_settings,
)

from telegram.ext import ContextTypes

# Logger per questo modulo
logger = logging.getLogger(__name__)

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
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Crea la tabella se non esiste
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS precipitation (
                    date TEXT PRIMARY KEY,        -- Data in formato ISO (YYYY-MM-DD)
                    is_rain BOOLEAN,              -- True se ha piovuto quel giorno
                    rain_mm REAL,                 -- Quantità di pioggia in mm (opzionale)
                    updated_at TEXT,              -- Timestamp ultima modifica (ISO)
                    manual BOOLEAN DEFAULT FALSE  -- True se modificato manualmente
                )
            """)

            now_iso = datetime.now(timezone.utc).isoformat()

            for day_data in days:
                # Aggiorna solo record automatici (non manuali) per evitare sovrascritture
                cursor.execute(
                    """
                    UPDATE precipitation
                    SET is_rain = ?, rain_mm = ?, updated_at = ?
                    WHERE date = ? AND manual = FALSE
                """,
                    (
                        day_data.is_rain,
                        day_data.rain_mm,
                        now_iso,
                        day_data.date,
                    ),
                )

                # Inserisce nuovo record se non esiste (non sovrascrive manuali)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO precipitation (date, is_rain, rain_mm, updated_at, manual)
                    VALUES (?, ?, ?, ?, FALSE)
                """,
                    (
                        day_data.date,
                        day_data.is_rain,
                        day_data.rain_mm,
                        now_iso,
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
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now().date().isoformat(),
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
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now().date().isoformat(),
                ),
            )

            conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Errore resettando il DB: {exc}") from exc


async def get_daily_precipitation(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Recupera i dati di precipitazione giornaliera dall'API Open-Meteo e li salva nel DB.

    Effettua una chiamata all'API con parametri basati sulla configurazione:
    - Coordinate geografiche
    - Range giorni passati/futuri
    - Soglia pioggia per considerare "pioggia"

    Raises:
        RuntimeError: Se ci sono errori nella chiamata API o nel parsing
    """
    try:
        wtr_settings = get_weather_settings()
        irr_settings = get_irrigation_settings()

        # Parametri per la chiamata API Open-Meteo
        params = {
            "latitude": wtr_settings["latitude"],  # Latitudine posizione
            "longitude": wtr_settings["longitude"],  # Longitudine posizione
            "daily": "precipitation_sum",  # Richiedi somma precipitazione giornaliera
            "timezone": "Europe/Rome",  # Fuso orario italiano
            "forecast_days": irr_settings["range_future_days"]
            + 1,  # Giorni previsione + oggi
            "past_days": irr_settings["range_past_days"],  # Giorni passati da includere
        }

        # import httpx

        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         wtr_settings["api_url"],
        #         params=params,
        #         timeout=10,)

        # Chiamata API con timeout di 10 secondi
        response = requests.get(wtr_settings["api_url"], params=params, timeout=10)
        response.raise_for_status()  # Solleva eccezione per errori HTTP

        logger.debug(f"API meteo chiamata con params: {params}")

        # Parsing della risposta JSON
        data = response.json()
        dates = data["daily"]["time"]  # Lista date ISO
        precipitation = data["daily"]["precipitation_sum"]  # Lista mm pioggia per data

        # Converte in oggetti tipizzati basandosi sulla soglia
        result = [
            DailyPrecipitation(
                date=day,
                is_rain=rain_mm > irr_settings["rain_threshold_mm"],
                rain_mm=rain_mm,
            )
            for day, rain_mm in zip(dates, precipitation)
        ]
        save_to_db_from_api(result)

    except requests.RequestException as exc:
        raise RuntimeError(f"Errore recuperando dati meteo: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"Errore parsing risposta meteo: {exc}") from exc


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

            # # Controlla se la tabella precipitation ha dati
            # cursor.execute("SELECT COUNT(*) FROM precipitation")
            # count = cursor.fetchone()[0]
            # if count != 0:
            #     return
            # else:
            #     try:
            #         get_daily_precipitation()  # Aggiorna i dati meteo se la tabella è vuota
            #     except RuntimeError as exc:
            #         logger.warning(f"Impossibile aggiornare i dati meteo: {exc}")

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
