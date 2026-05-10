from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from data_manager import update_db_from_telegram
from config_reader import get_telegram_settings
from bll_watering import should_irrigate


# =========================
# COMANDO MANUALE /w
# =========================
async def w_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        update_db_from_telegram()
        await update.message.reply_text("✅ OK!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore durante l'update:\n{e}")


# =========================
# JOB AUTOMATICO OGNI 4 ORE
# =========================
async def irrigation_check(context: ContextTypes.DEFAULT_TYPE):
    try:

        result = should_irrigate()

        chat_id = get_telegram_settings()["chat_id"]

        if result:
            message = "💧 Irrigazione NECESSARIA"
        else:
            message = "🌧️ Irrigazione NON necessaria"

        await context.bot.send_message(chat_id=chat_id, text=message)

    except Exception as e:
        chat_id = get_telegram_settings()["chat_id"]

        await context.bot.send_message(
            chat_id=chat_id, text=f"❌ Errore nel controllo irrigazione:\n{e}"
        )


def main():
    settings = get_telegram_settings()

    TOKEN = settings["token"]

    app = ApplicationBuilder().token(TOKEN).build()

    # comando manuale
    app.add_handler(CommandHandler("w", w_command))

    # =========================
    # JOB OGNI 4 ORE
    # =========================
    job_queue = app.job_queue

    job_queue.run_repeating(
        irrigation_check,
        interval=4 * 60 * 60,  # 4 ore
        first=10,  # parte dopo 10 secondi
    )

    print("Il treno ha fischiato!")

    app.run_polling()


if __name__ == "__main__":
    main()
