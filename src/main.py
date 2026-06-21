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
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from bll_watering import should_irrigate
from config_reader import get_telegram_settings, get_weather_settings, get_current_dir
from data_manager import (
    reset_today_precipitation,
    update_db_from_telegram,
    get_all_precipitation_data,
    get_daily_precipitation,
    create_db_if_not_exists,
)

# === CONFIGURAZIONE LOGGING ===
# Legge il livello di log dalla configurazione, WARNING di default se non specificato o errato
log_level_str = get_telegram_settings().get("log_level", "WARNING").upper()
log_level = getattr(logging, log_level_str, logging.WARNING)

# Configura il logging globale per tutti i moduli
logging.basicConfig(
    filename=get_current_dir().parent
    / "log.txt",  # File di log nella root del progetto
    encoding="utf-8",
    filemode="a",  # Append mode (accumula i log)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Formato log
    level=log_level,  # Livello globale letto da config
)

# Logger specifico per questo modulo
logger = logging.getLogger(__name__)

# Silenzia i log dettagliati della libreria telegram (solo errori critici)
logging.getLogger("telegram").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.ERROR)


# async def w_command(update: Update) -> None:
async def w_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestore del comando /db.

    Invia i dati di precipitazione dal database.
    Di default gli ultimi 7 giorni, altrimenti tutto se specificato "all".

    """
    try:
        args = update.message.text.split()[1:]  # Ottieni argomenti dopo /db
        show_all = len(args) > 0 and args[0].lower() == "all"

        data = get_all_precipitation_data()

        if not show_all:
            # Filtra ultimi N giorni (da config), partendo dalla data massima nel DB
            days = (
                get_telegram_settings().get("days_read_from_db", 7) - 1
            )  # -1 perché include oggi
            if data:
                max_date = max(d["date"] for d in data)
                n_days_ago = (
                    (datetime.fromisoformat(max_date) - timedelta(days=days))
                    .date()
                    .isoformat()
                )
            else:
                n_days_ago = (datetime.now() - timedelta(days=days)).date().isoformat()
            data = [d for d in data if d["date"] >= n_days_ago]

        if not data:
            await update.message.reply_text("Nessun dato trovato.")
            return

        # Formatta i dati
        today_iso = datetime.now().date().isoformat()
        lines = ["📅 Dati precipitazione:"]
        for d in data:
            date_str = datetime.fromisoformat(d["date"]).strftime("%d-%m-%Y")
            rain_str = f"{(d['rain_mm'])}mm" if d["rain_mm"] is not None else ""
            manual_str = "(manuale)" if d["manual"] else ""
            lines.append(
                f"{date_str if d['date'] != today_iso else '-- O G G I --'} {'✅' if d['is_rain'] else '❌'} {rain_str}{manual_str}"
            )

        message = "\n".join(lines)
        await update.message.reply_text(message)
    except Exception:
        logger.exception("Errore durante il comando /db")
        await update.message.reply_text(
            "❌ Errore durante la lettura del DB. Controlla i log del bot."
        )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestore del comando /reset.

    Resetta i dati di precipitazione per oggi, segnando che non ha piovuto.
    Utile se si è commesso un errore con il comando /w o per test.

    """
    try:
        reset_today_precipitation()  # Resetta i dati di oggi nel DB
        await update.message.reply_text("✅ Dati di oggi resettati!")
    except Exception:
        logger.exception("Errore durante il reset da Telegram")
        await update.message.reply_text(
            "❌ Errore durante il reset. Controlla i log del bot."
        )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestore del comando /today.

    Informa se oggi è necessario irrigare basandosi sui dati attuali.

    """
    try:
        result = should_irrigate()  # Logica: deve irrigare?
        message = (
            "💧 Oggi è NECESSARIO irrigare"
            if result
            else "🌧️ Oggi NON è necessario irrigare"
        )
        await update.message.reply_text(message)
    except Exception:
        logger.exception("Errore durante il comando /today")
        await update.message.reply_text(
            "❌ Errore durante il controllo di oggi. Controlla i log del bot."
        )


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestore del comando /update.

    Forza un aggiornamento dei dati di precipitazione dal servizio meteo.
    Utile per test o se si sospettano dati obsoleti.

    """
    try:
        await get_daily_precipitation(context)  # Forza aggiornamento dati
        await update.message.reply_text("✅ Dati aggiornati!")
    except Exception:
        logger.exception("Errore durante l'aggiornamento da Telegram")
        await update.message.reply_text(
            "❌ Errore durante l'aggiornamento. Controlla i log del bot."
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
        necessary_confirm = bool(
            get_telegram_settings().get("not_necessary_irrigation_confirm", False)
        )

        # Invia messaggio solo se irrigazione necessaria, o se configurato per notificare anche quando non necessaria
        if result or necessary_confirm:
            message = (
                "💧 Irrigazione NECESSARIA"
                if result
                else "🌧️ Irrigazione NON necessaria"
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

        txt = f"Bot Telegram creato con token: {token[:4]}****"
        print(txt)  # Stampa parziale del token per sicurezza
        logger.debug(txt)  # Log parziale del token per sicurezza

        # Registra i comandi
        app.add_handler(CommandHandler("w", w_command))
        app.add_handler(CommandHandler("db", db_command))
        app.add_handler(CommandHandler("reset", reset_command))
        app.add_handler(CommandHandler("today", today_command))
        app.add_handler(CommandHandler("update", update_command))

        create_db_if_not_exists()  # Assicurati che il DB esista prima di avviare il bot

        # Refresh dati precipitazione ogni X ore (configurato)
        app.job_queue.run_repeating(
            get_daily_precipitation,
            interval=get_weather_settings()["interval_check"],  # Ogni X secondi
            first=30,  # Aspetta 30 secondi prima del primo controllo
            name="daily_precipitation_job",
            job_kwargs={
                "misfire_grace_time": 300,  # 5 minuti
                "coalesce": True,
                "max_instances": 1,
            },
        )

        times = get_telegram_settings()["notification_time"]

        # Per ogni orario configurato, pianifica un job per controllare l'irrigazione e inviare le notifiche
        for t in times:
            hour, minute = map(int, t.strip().split(":"))

            app.job_queue.run_daily(
                irrigation_check,
                time=time(hour=hour, minute=minute, tzinfo=ZoneInfo("Europe/Rome")),
                name=f"irrigation_check_{hour}_{minute}",
                job_kwargs={
                    "misfire_grace_time": 300,  # 5 minuti
                    "coalesce": True,
                    "max_instances": 1,
                },
            )

        logger.debug(
            f"Bot avviato: comandi /w e /db disponibili, job pianificato ogni {get_weather_settings()['interval_check'] // 3600} ore"
        )
        app.run_polling()  # Avvia il loop di ricezione messaggi
        return 0
    except Exception:
        logger.exception("Impossibile avviare il bot")
        return 1


if __name__ == "__main__":
    sys.exit(main())
