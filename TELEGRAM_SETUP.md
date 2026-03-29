# Telegram Alert Setup Guide

Telegram alerts are **INSTANT** (real-time push notifications) - much faster than Gmail!

## Quick Setup (5 minutes)

### Step 1: Create a Telegram Bot

1. Open **Telegram** app (phone or desktop)
2. Search for: **@BotFather**
3. Send: `/start`
4. Send: `/newbot`
5. Answer the questions:
   - **Bot name:** `Patient Alert Bot` (or any name you want)
   - **Bot username:** `patient_alert_bot_XXXXX` (must be unique, ends with `_bot`)
6. **Copy the token** it gives you
   - Looks like: `123456789:ABCdefGHIjklmnOP...QRSTuvwxyz`

### Step 2: Get Your Chat ID

1. Search for: **@userinfobot**
2. Send: `/start`
3. It will show your **Chat ID** (a number like: `987654321`)
4. **Copy this number**

### Step 3: Configure .env File

1. Open `.env` file in the project root
2. Add these lines:
   ```
   TELEGRAM_BOT_TOKEN=paste_your_token_here
   TELEGRAM_CHAT_ID=paste_your_chat_id_here
   ```

3. Example (with fake credentials):
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmnOPQRSTuvwxyz123456789
   TELEGRAM_CHAT_ID=987654321
   ```

### Step 4: Test Your Bot

1. Go back to Telegram
2. Search for your bot name (from Step 1, e.g., `patient_alert_bot_XXXXX`)
3. Send any message
4. Your bot should be connected

## How Alerts Work

When the system detects an urgent task (Help, Pain, Medicine, Fever):

1. **Telegram Alert** → Instant push notification (appears in seconds!)
2. **Gmail Alert** → Sent as backup (arrives in 1-2 minutes)

## Alert Examples

When Help is selected 4+ times:
```
🚨 PATIENT ALERT 🚨

Task: HELP
Message: "Help me please"

⏰ Please respond immediately!
```

## Troubleshooting

### No alerts arriving?
- Check that bot token is correct (copy from @BotFather)
- Check that chat ID is correct (copy from @userinfobot)
- Verify .env file has correct variable names: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

### Want to keep only Telegram (no Gmail)?
- Leave EMAIL_USER, EMAIL_PASSWORD, and TO_EMAIL empty in .env
- Telegram will be your only alert source

### Want both Telegram AND Gmail?
- Just fill in both sections in .env
- Alerts go to both instantly

## Security Notes

⚠️ **Never share your bot token** - it's like a password
⚠️ **Never commit .env file to git** - use .env.example instead
⚠️ The bot can only message your Chat ID - no one else can use it

## More Help

- Telegram Bot API docs: https://core.telegram.org/bots
- @BotFather help: Send `/help` to @BotFather
