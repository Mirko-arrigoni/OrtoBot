#!/usr/bin/env python
"""
Bot Telegram per la gestione dell'irrigazione dell'orto.

Questo script avvia un bot Telegram che:
- Riceve comandi manuali per confermare l'irrigazione
- Controlla automaticamente ogni X ore se è necessario irrigare
- Invia notifiche basate sui dati meteorologici

Il bot usa la libreria python-telegram-bot per l'interfaccia Telegram
e un database SQLite per memorizzare i dati di precipitazione.
"""

import logging
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from bll_watering import should_irrigate
from config_reader import get_telegram_settings, get_weather_settings, get_current_dir
from data_manager import update_db_from_telegram

# === CONFIGURAZIONE LOGGING ===
# Legge il livello di log dalla configurazione, WARNING di default se non specificato o errato
log_level_str = get_telegram_settings().get("log_level", "WARNING").upper()
log_level = getattr(logging, log_level_str, logging.WARNING)

# Configura il logging globale per tutti i moduli
logging.basicConfig(
    filename=get_current_dir().parent / "log.txt",  # File di log nella root del progetto
    encoding="utf-8",
    filemode="a",                                   # Append mode (accumula i log)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Formato log
    level=log_level,  # Livello globale letto da config
)

# Logger specifico per questo modulo
logger = logging.getLogger(__name__)

# Silenzia i log dettagliati della libreria telegram (solo errori critici)
logging.getLogger("telegram").setLevel(logging.CRITICAL)


async def w_command(update: Update) -> None:
    """
    Gestore del comando /w (watering).

    Quando l'utente invia "/w", registra che oggi ha irrigato l'orto.
    Questo aggiorna il database impostando pioggia manuale per oggi.

    """
    try:
        update_db_from_telegram()  # Registra irrigazione manuale nel DB
        await update.message.reply_text("✅ OK!")
    except Exception:
        logger.exception("Errore durante l'update da Telegram")
        await update.message.reply_text(
            "❌ Errore durante l'update. Controlla i log del bot."
        )


async def irrigation_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Task periodico che controlla se è necessario irrigare.

    Viene eseguito automaticamente ogni X ore (configurato).
    Determina se irrigare basandosi sui dati meteo e invia notifica su Telegram.

    """
    try:
        result = should_irrigate()  # Logica: deve irrigare?
        chat_id = get_telegram_settings()["chat_id"]
        necessary_confirm = get_telegram_settings().get("not_necessary_irrigation_confirm", False)

        # Invia messaggio solo se irrigazione necessaria, o se configurato per notificare anche quando non necessaria
        if result or necessary_confirm:
            message = (
                "💧 Irrigazione NECESSARIA" if result else "🌧️ Irrigazione NON necessaria"
            )
            await context.bot.send_message(chat_id=chat_id, text=message)
    except Exception:
        logger.exception("Errore nel controllo irrigazione")
        try:
            # Tenta di inviare notifica di errore
            await context.bot.send_message(
                chat_id=get_telegram_settings()["chat_id"],
                text="❌ Errore nel controllo irrigazione. Controlla i log del bot.",
            )
        except Exception:
            logger.exception("Impossibile inviare il messaggio di errore su Telegram")


def main() -> int:
    """
    Funzione principale che avvia il bot Telegram.

    Configura:
    - L'applicazione Telegram con il token
    - I comandi disponibili (/w)
    - Il job periodico per il controllo irrigazione
    - Avvia il polling per ricevere messaggi

    Returns:
        int: 0 se successo, 1 se errore
    """
    try:
        token = get_telegram_settings()["token"]

        # Crea l'applicazione Telegram
        app = ApplicationBuilder().token(token).build()

        # Registra il comando /w
        app.add_handler(CommandHandler("w", w_command))

        # Pianifica il controllo periodico dell'irrigazione
        app.job_queue.run_repeating(
            irrigation_check,
            interval=get_weather_settings()["interval_check"],  # Ogni X secondi
            first=10,  # Aspetta 10 secondi prima del primo controllo
        )

        logger.info("Bot avviato: in ascolto e job pianificato ogni 4 ore")
        app.run_polling()  # Avvia il loop di ricezione messaggi
        return 0
    except Exception:
        logger.exception("Impossibile avviare il bot")
        return 1


if __name__ == "__main__":
    sys.exit(main())
