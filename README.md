# IvaSMS Selenium Bot

Telegram bot for automating SMS retrieval from IvaSMS.com using Selenium with "Headed" Chrome support (via Xvfb).

## Features
- **Auto-Login**: Automatically logs in to IvaSMS.
- **Smart SMS Fetching**: Parses Google codes, OTPs, and generic messages.
- **Admin Panel**: Manage stock, broadcast messages, and view stats.
- **Docker Support**: "2026-ready" deployment with a single command.
- **Stealth Mode**: Uses `undetected-chromedriver` and Xvfb to run a real Chrome browser in a virtual display, avoiding bot detection.

## 🚀 Deployment (VPS / Docker)

This is the recommended way to run the bot 24/7.

### 1. Requirements
- A VPS (Ubuntu/Debian recommended)
- Docker & Docker Compose installed

### 2. Setup
Clone this repository and enter the folder:
```bash
git clone https://github.com/YOUR_USERNAME/ivas_selenium_bot.git
cd ivas_selenium_bot
```

### 3. Configure
Rename `.env.example` to `.env` (or create it) and fill in your details:
```ini
BOT_TOKEN=your_bot_token
ADMIN_CHAT_IDS=12345678,87654321
IVAS_EMAIL=your_email
IVAS_PASSWORD=your_password
```

### 4. Run
Start the bot in the background:
```bash
docker-compose up -d --build
```

### 5. Management
- **View Logs**: `docker-compose logs -f`
- **Restart**: `docker-compose restart`
- **Stop**: `docker-compose down`

## 🛠️ Local Development (Windows)
1. Install Python 3.10+
2. Install Chrome
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python main.py`
