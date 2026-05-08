from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from data_manager import update_db_from_telegram
from config_reader import get_telegram_settings
from bll_watering import should_irrigate

# Comando /w
async def w_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Quando l'utente scrive /w, chiama updatedb_fromTelegram e risponde con conferma/errore.
    """
    try:
        update_db_from_telegram() 
        await update.message.reply_text("✅ OK!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore durante l'update:\n{e}")

def main():
    TOKEN = get_telegram_settings()["token"]  # Ottieni il token dal file di configurazione
    
    # Costruisci l'applicazione del bot
    app = ApplicationBuilder().token(TOKEN).build()

    # Aggiungi il comando /w
    app.add_handler(CommandHandler("w", w_command))

    # Avvia il bot
    print("Il treno ha fischiato!")
    app.run_polling()

if __name__ == "__main__":
    main()