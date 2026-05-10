from datetime import date
from data_manager import get_precipitation_from_db
from config_reader import get_irrigation_settings


def should_irrigate() -> bool:
    """
    Ritorna se oggi deve irrigare o no, basandosi sulle precipitazioni passate e future.

    Pseudocodice:
    SE oggi - ultimo_giorno_precipitazione > soglia (4gg) ALLORA

        SE prossimo_giorno_precipitazione - oggi > soglia_2 (2gg) ALLORA
            irrigazione ON
        ALTRIMENTI
            irrigazione OFF (viene saltata l'irrigazione)

    ALTRIMENTI
        irrigazione OFF


    per irrigazione ON si intende l'invio della notifica su telegram.
    Poi sta all'utente effettivamente mandare il comando per salvare il giorno corrente come ultimo_giorno_precipitazione (se non sovrascritto dal meteo).
    """

    config = get_irrigation_settings()
    soglia_past = config["range_past_days"]
    soglia_futura = config["range_future_days"]

    today = date.today()
    precipitation_calendar = get_precipitation_from_db()
    past_precipitation = [
        date.fromisoformat(day)
        for day, is_rain in precipitation_calendar.items()
        if is_rain and date.fromisoformat(day) < today
    ]
    future_precipitation = [
        date.fromisoformat(day)
        for day, is_rain in precipitation_calendar.items()
        if is_rain and date.fromisoformat(day) >= today
    ]

    # Se non ha mai piovuto, le variabili sono None.
    last_rain_date = max(past_precipitation) if past_precipitation else None
    next_rain_date = min(future_precipitation) if future_precipitation else None

    if last_rain_date is None or (today - last_rain_date).days > soglia_past:
        if next_rain_date is None or (next_rain_date - today).days > soglia_futura:
            return True
    return False
