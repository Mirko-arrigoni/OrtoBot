from pathlib import Path
import toml

def getCurrentDir() -> Path:
    return Path(__file__).parent.resolve()  # /home/dietpi/orto/src

def getConfig() -> dict:
    path = getCurrentDir().parent / "conf/env.toml"  # /home/dietpi/orto/conf/env.toml
    with open(path, "r") as f:
        config = toml.load(f)
    return config

def getWeatherConfig() -> dict:
    return getConfig()["coordinates"]

def getIrrigationSettings() -> dict:
    return getConfig()["irrigationSettings"]

def getUrlAPI() -> str:
    return getIrrigationSettings()["urlAPImeteo"]

def getTelegramSettings() -> dict:
    return getConfig()["telegram"]