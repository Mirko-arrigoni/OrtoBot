"""
Modulo per la gestione delle chiamate API per il recupero dei dati meteo.
Utilizza la libreria requests per effettuare chiamate HTTP e gestisce eventuali errori
"""

import logging
from datetime import datetime

import requests

from config_reader import (
    get_irrigation_settings,
    get_weather_settings,
)

from data_manager import DailyPrecipitation, save_to_db_from_api
from telegram.ext import ContextTypes

# Logger per questo modulo
logger = logging.getLogger(__name__)


def _to_hhmm(value: str | None) -> str | None:
    """Converte un valore ISO datetime in stringa HH:MM."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%H:%M")
    except ValueError:
        logger.warning("Orario non valido ricevuto dall'API: %r", value)
        return str(value)


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
            "daily": ["sunrise", "sunset", "precipitation_sum"],  # Richiedi somma precipitazione giornaliera
            "timezone": "Europe/Rome",  # Fuso orario italiano
            "forecast_days": irr_settings["range_future_days"] + 1,  # Giorni previsione + oggi
            "past_days": irr_settings["range_past_days"],  # Giorni passati da includere
        }

        # Chiamata API con timeout di 10 secondi
        response = requests.get(wtr_settings["api_url"], params=params, timeout=10)
        response.raise_for_status()  # Solleva eccezione per errori HTTP

        logger.debug(f"API meteo chiamata con params: {params}")

        # Parsing della risposta JSON
        data = response.json()
        dates = data["daily"]["time"]  # Lista date ISO
        precipitation = data["daily"]["precipitation_sum"]  # Lista mm pioggia per data
        sunrise_times = data["daily"]["sunrise"]  # Lista orari alba
        sunset_times = data["daily"]["sunset"]  # Lista orari tramonti

        # Converte in oggetti tipizzati basandosi sulla soglia
        result = [
            DailyPrecipitation(
                date=day,
                is_rain=rain_mm > irr_settings["rain_threshold_mm"],
                rain_mm=rain_mm,
                sunrise=_to_hhmm(sunrise_time),
                sunset=_to_hhmm(sunset_time),
            )
            for day, rain_mm, sunrise_time, sunset_time in zip(dates, precipitation, sunrise_times, sunset_times)
        ]
        save_to_db_from_api(result)

    except requests.RequestException as exc:
        raise RuntimeError(f"Errore recuperando dati meteo: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"Errore parsing risposta meteo: {exc}") from exc