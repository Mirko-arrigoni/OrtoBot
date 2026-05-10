from pathlib import Path
import toml


def get_current_dir() -> Path:
    return Path(__file__).parent.resolve()  # /home/dietpi/orto/src


def get_config() -> dict:
    path = get_current_dir().parent / "conf/env.toml"  # /home/dietpi/orto/conf/env.toml
    with open(path, "r") as f:
        config = toml.load(f)
    return config


def get_telegram_settings() -> dict:
    return get_config()["telegram"]


def get_weather_settings() -> dict:
    return get_config()["weather"]


def get_irrigation_settings() -> dict:
    return get_config()["irrigation"]


def get_database_settings() -> dict:
    return get_config()["database"]
