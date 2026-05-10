"""
Modulo per la lettura e gestione della configurazione.
Carica i parametri dal file TOML e fornisce interfacce tipizzate per accedere alle varie sezioni.
"""

from functools import lru_cache
from pathlib import Path

import toml


def get_current_dir() -> Path:
    """Ritorna il percorso assoluto della directory corrente (src/)."""
    return Path(__file__).parent.resolve()


@lru_cache(maxsize=1)
def get_config() -> dict:
    """
    Carica e cache la configurazione completa dal file env.toml.

    Il file si trova in ../conf/env.toml rispetto a questo script.
    La configurazione viene cachata per evitare riletture multiple.

    Returns:
        dict: Configurazione completa caricata dal TOML

    Raises:
        RuntimeError: Se il file non esiste, è malformato o non può essere letto
    """
    path = get_current_dir().parent / "conf/env.toml"
    try:
        with open(path, "r") as f:
            config = toml.load(f)
    except FileNotFoundError as exc:
        raise RuntimeError(f"File configurazione non trovato: {path}") from exc
    except toml.TomlDecodeError as exc:
        raise RuntimeError(f"Errore parsing TOML in {path}: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Errore lettura {path}: {exc}") from exc
    return config


def _get_config_section(section: str) -> dict:
    """
    Helper privato per ottenere una sezione specifica della configurazione.

    Args:
        section: Nome della sezione da recuperare (es. "telegram", "weather")

    Returns:
        dict: La sezione richiesta della configurazione

    Raises:
        RuntimeError: Se la sezione non esiste nel file di configurazione
    """
    config = get_config()
    try:
        return config[section]
    except KeyError as exc:
        raise RuntimeError(f"Sezione '{section}' mancante in configurazione") from exc


def get_telegram_settings() -> dict:
    """Ritorna le impostazioni relative a Telegram (token, chat_id, log_level, etc.)."""
    return _get_config_section("telegram")


def get_weather_settings() -> dict:
    """Ritorna le impostazioni relative al meteo (coordinate, API, soglie)."""
    return _get_config_section("weather")


def get_irrigation_settings() -> dict:
    """Ritorna le impostazioni relative all'irrigazione (soglie giorni, range)."""
    return _get_config_section("irrigation")


def get_database_settings() -> dict:
    """Ritorna le impostazioni relative al database (nome file, etc.)."""
    return _get_config_section("database")
