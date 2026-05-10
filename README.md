# 🌱 OrtoBot - Assistente Automatico per l'Irrigazione

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API-blue.svg)](https://core.telegram.org/bots/api)
[![SQLite](https://img.shields.io/badge/SQLite-Database-green.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un bot Telegram intelligente che decide automaticamente quando irrigare l'orto basandosi sui dati meteorologici reali. Combina previsioni del tempo, dati storici e logica personalizzabile per ottimizzare l'uso dell'acqua.

## ✨ Caratteristiche Principali

- 🤖 **Bot Telegram Interattivo**: Ricevi notifiche automatiche e comandi manuali
- 🌦️ **Dati Meteo Reali**: Integrazione con Open-Meteo API per previsioni accurate
- 🧠 **Logica Intelligente**: Algoritmo che considera pioggia passata e futura
- 📊 **Database Locale**: SQLite per storicizzare dati e modifiche manuali
- ⚙️ **Configurabile**: Personalizza soglie, intervalli e comportamenti
- 📝 **Logging Completo**: Traccia tutte le operazioni per debugging
- 🔄 **Aggiornamenti Automatici**: Controlli periodici senza intervento manuale

## 🚀 Come Funziona

1. **Raccolta Dati**: Scarica automaticamente previsioni meteo per i prossimi giorni
2. **Analisi Intelligente**: Valuta se irrigare basandosi su:
   - Giorni senza pioggia recenti
   - Previsioni pioggia future
   - Modifiche manuali dell'utente
3. **Notifiche Smart**: Invia messaggi Telegram solo quando necessario
4. **Interazione**: Permette conferme manuali quando irrighi

### Logica di Decisione

```
SE non piove da più di X giorni
   E non pioverà nei prossimi Y giorni
   ALLORA → Irrigazione NECESSARIA
ALTRIMENTI → Irrigazione NON necessaria
```

## 📦 Installazione

### Prerequisiti

- Python 3.11 o superiore
- Token Bot Telegram (da [@BotFather](https://t.me/botfather))
- Chat ID Telegram (vedi sezione Configurazione)

### Setup

1. **Clona il repository**
   ```bash
   git clone https://github.com/Mirko-arrigoni/orto-bot.git
   cd orto-bot
   ```

2. **Crea ambiente virtuale**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # oppure: venv\Scripts\activate  # Windows
   ```

3. **Installa dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura il bot**
   ```bash
   cp conf/config.example.toml conf/env.toml
   # Modifica conf/env.toml con i tuoi parametri
   ```

5. **Avvia il bot**
   ```bash
   python src/main.py
   ```

## ⚙️ Configurazione

Copia `conf/config.example.toml` in `conf/env.toml` e configura:

### Telegram
```toml
[telegram]
chat_id = 123456789          # Il tuo Chat ID Telegram
token = "your-bot-token"     # Token dal BotFather
log_level = "INFO"           # DEBUG, INFO, WARNING, ERROR
not_necessary_irrigation_confirm = false  # Ricevi notifiche anche quando non serve irrigare?
```

### Meteo
```toml
[weather]
latitude = "45.20"           # Latitudine della tua posizione
longitude = "9.34"           # Longitudine della tua posizione
api_url = "https://api.open-meteo.com/v1/forecast"
rain_threshold_mm = 3        # Quanti mm di pioggia contano come "pioggia"
interval_check = 14400       # Secondi tra controlli automatici (4 ore)
```

### Irrigazione
```toml
[watering]
range_past_days = 4          # Giorni senza pioggia per considerare irrigazione
range_future_days = 2        # Giorni previsione per evitare irrigazione inutile
rain_threshold_mm = 6        # Soglia pioggia per bloccare irrigazione
```

### Database
```toml
[database]
name = "weather.db"          # File SQLite per i dati
```

## 📱 Utilizzo

### Comandi Telegram

- **`/start`**: Avvia il bot (automatico)
- **`/w`**: Conferma che hai irrigato oggi

### Notifiche Automatiche

Il bot invia messaggi ogni 4 ore (configurabile):

- 💧 **"Irrigazione NECESSARIA"** - Devi irrigare
- 🌧️ **"Irrigazione NON necessaria"** - Non serve per ora

### Ottieni Chat ID

Per trovare il tuo Chat ID:

1. Avvia il bot su Telegram
2. Invia un messaggio qualsiasi
3. Controlla i log del bot o usa un bot come [@userinfobot](https://t.me/userinfobot)

## 📁 Struttura Progetto

```
orto-bot/
├── src/                    # Codice sorgente
│   ├── main.py            # Bot Telegram principale
│   ├── config_reader.py   # Gestione configurazione
│   ├── data_manager.py    # Database e API meteo
│   └── bll_watering.py    # Logica irrigazione
├── conf/                   # Configurazioni
│   ├── config.example.toml # Template configurazione
│   └── env.toml           # Configurazione personale (non committare!)
├── pyproject.toml         # Dipendenze e metadata Python
├── README.md              # Questa guida
└── log.txt               # File di log (generato)
```

## 🛠️ Tecnologie

- **Python 3.11+**: Linguaggio principale
- **python-telegram-bot**: Interfaccia Telegram
- **requests-cache + retry-requests**: API HTTP con cache
- **SQLite**: Database locale
- **TOML**: Configurazioni
- **Open-Meteo API**: Dati meteorologici gratuiti

## 🤝 Contributi

Contributi benvenuti! Per contribuire:

1. Fork il progetto
2. Crea un branch per la tua feature (`git checkout -b feature/nuova-funzionalità`)
3. Committa le modifiche (`git commit -am 'Aggiunge nuova funzionalità'`)
4. Pusha il branch (`git push origin feature/nuova-funzionalità`)
5. Apri una Pull Request

### Idee per Contributi

- 🌐 Supporto per altre API meteo
- 📊 Dashboard web per statistiche
- 📱 App mobile companion
- 🌍 Localizzazione in altre lingue
- 🔧 Configurazione via comandi Telegram

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per i dettagli.

## 🙏 Ringraziamenti

- [Open-Meteo](https://open-meteo.com/) per l'API meteo gratuita
- [Python Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot) per la libreria
- La comunità open source per gli strumenti utilizzati

## 📞 Supporto

Hai problemi? Apri una [issue](https://github.com/Mirko-arrigoni/orto-bot/issues) su GitHub!

---

*Creato con ❤️ per ottimizzare l'irrigazione e risparmiare acqua* 🌱💧
