from datetime import date
from weather import get_daily_precipitation
from configReader import getConfig
import sqlite3

config = getConfig()
freq = config["irrigation"]["frequency_days"]

def getPreviousWatering():
    cur = sqlite3.connect('irrigation.db').cursor()
    get_daily_precipitation(freq, type="historical")  # aggiorna il db con le precipitazioni passate
    #todo: aggiungere al db anche la data dell'irrigazione, in modo da poterla confrontare con le precipitazioni passate


def checkPreviousWatering():
    cur = sqlite3.connect('irrigation.db').cursor()
    last_watering = cur.execute("SELECT date from WATERING_HISTORY where rain = 1 ORDER BY date DESC LIMIT 1").fetchone()
    return last_watering[0] if last_watering else 99

def checkFutureWatering():
    rain_threshold = config["irrigation"]["rain_threshold_mm"]

    for i, day in get_daily_precipitation(freq).enumerate():
        if day >= rain_threshold:
            return date.today() + i

def should_water():
    last_watering = checkPreviousWatering()
    future_watering = checkFutureWatering()

    return (future_watering - last_watering).days > freq