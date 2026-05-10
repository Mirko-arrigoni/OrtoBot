"""
Modulo per la logica dell'irrigazione.
Contiene le funzioni per determinare se è necessario irrigare basandosi sui dati meteorologici.
"""

import logging
from datetime import date
from typing import Optional

from config_reader import get_irrigation_settings
from data_manager import get_precipitation_from_db

# Logger per questo modulo
logger = logging.getLogger(__name__)


def should_irrigate() -> bool:
    """
    Determina se oggi è necessario irrigare l'orto.

    La logica si basa sui dati di precipitazione passati e futuri:
    - Se non ha piovuto da più di X giorni (range_past_days), considera l'irrigazione
    - Ma se pioverà nei prossimi Y giorni (range_future_days), salta l'irrigazione

    Returns:
        bool: True se deve irrigare, False altrimenti

    Raises:
        Exception: Rilancia eventuali errori durante il calcolo
    """
    try:
        # Carica le impostazioni di irrigazione dal config
        config = get_irrigation_settings()
        gg_passati = config["range_past_days"]  # Giorni senza pioggia per attivare irrigazione
        gg_futuri = config["range_future_days"]  # Giorni futuri senza pioggia per confermare irrigazione

        today = date.today()
        precipitation_calendar = get_precipitation_from_db()

        # Filtra le date di pioggia nel passato (prima di oggi)
        past_precipitation = [
            date.fromisoformat(day)  # Converte stringa ISO in oggetto date
            for day, is_rain in precipitation_calendar.items()
            if is_rain and date.fromisoformat(day) < today  # Solo giorni di pioggia passati
        ]

        # Filtra le date di pioggia nel futuro (oggi incluso)
        future_precipitation = [
            date.fromisoformat(day)
            for day, is_rain in precipitation_calendar.items()
            if is_rain and date.fromisoformat(day) >= today  # Giorno di pioggia futuri
        ]

        # Trova l'ultima data di pioggia passata
        last_rain_date: Optional[date] = (
            max(past_precipitation) if past_precipitation else None
        )

        # Trova la prossima data di pioggia nel futuro
        next_rain_date: Optional[date] = (
            min(future_precipitation) if future_precipitation else None
        )

        # Logica di decisione irrigazione:
        # Irriga se:
        # 1. Non ha mai piovuto (last_rain_date is None) OPPURE sono passati troppi giorni dall'ultima pioggia
        # E
        # 2. Non pioverà presto (next_rain_date is None) OPPURE la prossima pioggia è troppo lontana
        should_water = (
            last_rain_date is None or (today - last_rain_date).days > gg_passati
        ) and (
            next_rain_date is None or (next_rain_date - today).days > gg_futuri
        )

        # Logga la decisione per debug
        logger.debug(
            "Decisione irrigazione: ultima pioggia=%s, prossima pioggia=%s, irrigare=%s",
            last_rain_date,
            next_rain_date,
            should_water,
        )

        return should_water

    except Exception:
        # Logga l'errore e rilancia per gestire upstream
        logger.exception("Errore nel calcolo dell'irrigazione")
        raise
