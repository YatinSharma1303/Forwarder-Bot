# 🚀 Complete Deployment Guide
## Telegram Forwarder Bot - Safety Edition

**From Zero to Deployed: Every Step Explained in Detail**

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Step 1: Clone the Repository](#-step-1-clone-the-repository)
3. [Step 2: Get API_ID & API_HASH (my.telegram.org)](#-step-2-get-api_id--api_hash-mytelegramorg)
4. [Step 3: Create Your Bot & Get BOT_TOKEN (@BotFather)](#-step-3-create-your-bot--get-bot_token-botfather)
5. [Step 4: Get Your ADMIN_ID (@userinfobot)](#-step-4-get-your-admin_id-userinfobot)
6. [Step 5: Generate Session String (SESSION_B64)](#-step-5-generate-session-string-session_b64)
7. [Step 6: Configure Environment Variables](#-step-6-configure-environment-variables)
8. [Step 7: Deploy to Railway](#-step-7-deploy-to-railway)
9. [Step 8: Test Your Bot](#-step-8-test-your-bot)
10. [Troubleshooting](#-troubleshooting)

---

## 📦 Prerequisites

Before you start, make sure you have:

| Item | Purpose | Where to Get |
|------|---------|--------------|
| **Telegram Account** | For API credentials & session | You already have this ✅ |
| **GitHub Account** | To clone & deploy code | github.com |
| **Railway Account** | To host the bot 24/7 | railway.app |
| **Phone Number** | Linked to Telegram | Your number |

---

## 📥 Step 1: Clone the Repository

### Option A: Clone via HTTPS (Recommended)

```bash
# Navigate to where you want the project
cd ~

# Clone the repository
git clone https://github.com/YatinSharma1303/Forwarder-Bot.git

# Enter the project directory
cd Forwarder-Bot
```

### Option B: Clone via SSH (If you have SSH keys set up)

```bash
git clone git@github.com:YatinSharma1303/Forwarder-Bot.git
cd Forwarder-Bot
```

### Verify Clone Success

You should see these files:
```
Forwarder-Bot/
├── bot.py              # Main bot file (Safety Edition)
├── login_once.py       # Session generator
├── session_manager.py  # Session utilities
├── .env.example        # Template for env vars
├── requirements.txt    # Python dependencies
├── Dockerfile          # Railway deployment config
├── railway.json        # Railway project settings
├── Procfile            # Process runner
├── README.md           # Documentation
└── DEPLOYMENT_GUIDE.md # THIS FILE ← You are here!
```

---

## 🔑 Step 2: Get API_ID & API_HASH (my.telegram.org)

These credentials identify your Telegram **user account** to Telethon. The bot uses YOUR account to read messages from source channels.

> ⚠️ **Important**: Use your REAL phone number. This is NOT the bot's token - it's your personal Telegram API access.

### Detailed Steps with Screenshots Guide:

#### Step 2.1: Open my.telegram.org

1. Open your web browser (Chrome/Firefox/Edge)
2. Go to: **https://my.telegram.org**
3. You will see this page:

```
┌─────────────────────────────────────┐
│                                     │
│         TELEGRAM                   │
│                                     ││    ┌─────────────────┐         │
│    │  Phone number   │         │
│    └─────────────────┘         │
│                                     │
│          [ Next ]                  │
│                                     │
└─────────────────────────────────────┘
```

#### Step 2.2: Enter Your Phone Number

1. In the "Phone number" field, enter your **complete phone number**
2. Format: `+` followed by country code and number
   
   Examples:
   - India: `+919876543210`
   - USA: `+15551234567`
   - UK: `+447911123456`

3. Click **[Next]** button

#### Step 2.3: Receive Login Code

1. Check your **Telegram app** on your phone
2. You will receive a message like this:
   ```
   ┌─────────────────────────────┐
   │  Telegram                   │
   │                             │
   │  Your login code: 12345     │
   │                             │
   │  Do not give this code      │
   │  to anyone, even if they    │
   │  say they work for Telegram!│
   └─────────────────────────────┘
   ```
   
3. **Note**: If you don't receive the code within 60 seconds:
   - Click "Resend code" on the website
   - Check your Telegram app notifications
   - Make sure you entered the correct phone number

#### Step 2.4: Enter the Code

1. Type the numeric code you received into the box
2. Click **[Log in]**

#### Step 2.5: Access API Development Tools

After successful login, you'll see:
```
┌─────────────────────────────────────┐
│                                     │
│    Hello, [Your Name]!             │
│                                     │
│    Please choose an option:         │
│                                     │
│    ○ Edit Profile                  │
│    ○ Active Sessions               │
│    ○ API development tools  ← CLICK│
│                                     │
└─────────────────────────────────────┘
```

Click on **"API development tools"**

#### Step 2.6: Create Application (First Time Only)

If this is your first time, you need to create an app:

**Fill in the form:**

| Field | What to Enter | Example |
|-------|---------------|---------|
| **App title** | Any name you want | `MyForwarderBot` |
| **Short name** | Short version (no spaces) | `forwarderbot` |
| **URL** | Leave blank or use `https://github.com` | `https://github.com` |
| **Platform** | Select "Desktop" or "Other" | Desktop |
| **Description** | Optional | `Personal use` |

Click **[Create application]**

#### Step 2.7: Copy Your Credentials

After creating/accessing the app, you will see:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  App configuration                                  │
│                                                     │
│  App api_id:                                        │
│  ════════════                                       │
│  12345678          ← THIS IS YOUR API_ID            │
│                                                     │
│  App api_hash:                                      │
│  ══════════════                                     │
│  abcdef1234567890abcdef1234567890  ← API_HASH       │
│                                                     │
│  [ WARNING: Do not share api_id or api_hash ]       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Copy both values carefully:**

```
API_ID = 12345678                    ← Just the numbers
API_HASH = abcdef1234567890abcdef1234567890  ← Alphanumeric string
```

> 🔒 **Keep these safe!** Anyone with these can impersonate your account.
> Save them somewhere secure - you'll need them for Railway deployment.

---

## 🤖 Step 3: Create Your Bot & Get BOT_TOKEN (@BotFather)

The BOT_TOKEN is used by python-telegram-bot library to control your bot and forward messages anonymously.

### Detailed Steps:

#### Step 3.1: Open @BotFather in Telegram

1. Open Telegram app (mobile or desktop)
2. Tap the **Search icon** (🔍) at the top right
3. Type: `@BotFather`
4. Tap on **@BotFather** (it should have a verified blue badge)

You should see:
```
┌─────────────────────────────────────┐
│  👤 @BotFather                      │
│                                     │
│  Official bot for creating bots.    │
│  Verified ✓                         │
│                                     │
│  [ Start ]                          │
└─────────────────────────────────────┘
```

5. Tap **[Start]** button at the bottom

#### Step 3.2: Create New Bot

1. Type `/newbot` and send it
2. BotFather will respond:
   ```
   Alright, a new bot. How are we going to name it?
   Choose a name for your bot.
   ```

3. **Enter a display name** (what users will see):
   ```
   My Forwarder Bot
   ```
   
   Or any name you prefer!

4. BotFather will ask for a **username**:
   ```
   Good. Now give your bot a username.
   It must end in `bot`. Like TetrisBot or tetris_bot.
   ```

5. **Enter a unique username** ending with `bot`:
   ```
   YatinForwarderBot
   ```
   
   > ⚠️ If the username is taken, try adding numbers or underscores:
   > - `YatinForwarderBot2024`
   > - `Yatin_Forwarder_Bot`
   > - `MyForwarderBot_xyz`

#### Step 3.3: Get Your Token

If successful, BotFather responds with:
```
Done! Congratulations on your new bot.

Name: My Forwarder Bot
Username: @YatinForwarderBot

Token: 7123456789:AAH1234567890abcdefghijklmnop
         ↑ THIS IS YOUR BOT_TOKEN ↑

You can now add a description, profile picture,
and list of commands for people to use.
```

**Copy the ENTIRE token string:**
```
BOT_TOKEN = 7123456789:AAH1234567890abcdefghijklmnop
```

> 💡 **Save this token securely!** Anyone with it can control your bot.
> Never share it publicly or commit it to GitHub.

#### Step 3.4: (Optional) Set Bot Commands

To make your bot look professional, set up commands:

1. Send `/setcommands` to @BotFather
2. Select your bot (`@YatinForwarderBot`)
3. Paste this list:

```
start - Start the bot / Show status
addsource - Add source channel/group
removesource - Remove source channel
listsources - List all sources
adddest - Add destination channel
removest - Remove destination
listdests - List all destinations
forward - Start forwarding
pause - Pause forwarding
resume - Resume forwarding
status - Show current status
stats - Show statistics
settings - Change safety settings
resetdaily - Reset daily counter
help - Show help message
private - Add private channel via link
cancel - Cancel current operation
```

4. Send the message

Your bot is now ready! 🎉

---

## 👤 Step 4: Get Your ADMIN_ID (@userinfobot)

The ADMIN_ID tells the bot who is allowed to control it. Only YOU should be able to use admin commands.

### Method 1: Using @userinfobot (Easiest)

#### Step 4.1: Open @userinfobot

1. Open Telegram
2. Search for `@userinfobot`
3. Tap on **@userinfobot**

#### Step 4.2: Send Any Message

1. Tap **[Start]** or type anything ("hi", "hello", etc.)
2. Send the message

#### Step 4.3: Copy Your User ID

The bot will respond instantly:
```
┌─────────────────────────────────────┐
│  Id: 987654321          ← THIS IS  │
│                        YOUR ADMIN_ID│
│  First Name: Yatin                   │
│                                     │
│  ...                                │
└─────────────────────────────────────┘
```

**Copy the number next to "Id":**
```
ADMIN_ID = 987654321
```

### Method 2: Using @RawDataBot (Alternative)

1. Search for `@RawDataBot` in Telegram
2. Send `/start`
3. It returns JSON with `"id": 987654321`
4. Copy that ID number

### Method 3: From Your Telegram Profile URL

1. Open your Telegram profile
2. Share your profile link (if you have a username)
3. Or check: `https://t.me/username` → userinfobot shows ID

> ⚠️ **Important**: ADMIN_ID must be a **number only**, no quotes, no extra characters.

---

## 🔐 Step 5: Generate Session String (SESSION_B64)

This is the MOST CRITICAL step. The session string allows the bot to log in as YOUR Telegram user account to read messages from **private channels** without needing to be added as a member.

### Prerequisites Before Starting:

- [x] You have API_ID and API_HASH (from Step 2)
- [x] Python installed on your computer
- [x] Telegram app open on your phone (to receive verification code)

### Step 5.1: Install Python Dependencies

Open terminal/command prompt in the project folder:

```bash
cd Forwarder-Bot

# Install required packages
pip install -r requirements.txt
```

This installs:
- `telethon` - For Telegram user session
- `python-telegram-bot` - For bot control
- `cryptography` - For session encryption

### Step 5.2: Run the Login Script

```bash
python login_once.py
```

### Step 5.3: Follow the Interactive Prompts

The script will guide you through:

```
╔══════════════════════════════════════════════════╗
║     TELEGRAM FORWARDER - SESSION GENERATOR       ║
╚══════════════════════════════════════════════════╝

This script generates a one-time session string for
reading from private channels/groups.

⚠️  Your phone number is ONLY used locally to create
the session. It is NEVER stored or sent anywhere.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Enter your API ID
> 
```

**Enter your API_ID** (from Step 2):
```
> 12345678
```

```
Step 2: Enter your API Hash
> 
```

**Enter your API_HASH** (from Step 2):
```
> abcdef1234567890abcdef1234567890
```

```
Step 3: Enter your phone number (with country code)
Example: +919876543210
> 
```

**Enter your phone number**:
```
> +919876543210
```

### Step 5.4: Receive Verification Code

The script will say:
```
Sending code to +91XXXXX43210...
```

Check your Telegram app:
```
┌─────────────────────────────┐
│  Telegram                   │
│                             │
│  Login code: 54321          │
│                             │
│  Valid for 5 minutes        │
└─────────────────────────────┘
```

**Enter the code when prompted:**
```
Enter the code you received: 54321
```

### Step 5.5: Handle Two-Factor Authentication (If Enabled)

If you have 2FA enabled on your Telegram account:

```
Your account has 2FA enabled.
Enter your password:
```

**Enter your 2FA password** (the one you set in Telegram Settings → Privacy → Two-Step Verification).

### Step 5.6: Copy Your Session String

After successful login, you'll see:

```
✅ Session created successfully!

╔══════════════════════════════════════════════════╗
║           COPY THIS SESSION STRING              ║
╚══════════════════════════════════════════════════╝

SESSION_B64=AZN6cF8KjXmPqRstUvWxYz1234567890abcdefGHIJ
KLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789
AAAAAABBBBBBCCCCCDDDDDEEEEEFFFFGGGGHHHIIIJJJKKKKLLL
MMMNNNOOOPPPQQQRRRSSSTTTUUUVVVWWWXXXYYYZZZ000111222
333444555666777888999000AAA==

╚══════════════════════════════════════════════════╝

↑ COPY EVERYTHING BETWEEN THE LINES ABOVE ↑

This is your SESSION_B64 value for Railway deployment.
```

**COPY THE ENTIRE SESSION_B64 VALUE** - it's a long string that may span multiple lines.

### Alternative: Using session_manager.py (Advanced)

If you already have a `session.session` file and want to convert it:

```bash
# Encode existing session to base64 string
python session_manager.py --encode

# Output:
# Session encoded successfully!
# SESSION_B64=AZN6cF8KjXmPqRstUvWxYz...
```

Other useful commands:
```bash
# Verify a session is valid
python session_manager.py --verify

# Decode base64 back to session file
python session_manager.py --decode <base64-string>
```

---

## ⚙️ Step 6: Configure Environment Variables

Now you have ALL the values needed. Let's configure them for deployment.

### Summary of All Environment Variables

| Variable | Description | Example Value | From Step |
|----------|-------------|---------------|-----------|
| `API_ID` | Your Telegram API ID | `12345678` | Step 2 |
| `API_HASH` | Your Telegram API hash | `abcdef123...` | Step 2 |
| `BOT_TOKEN` | Your bot token | `7123456:AAH...` | Step 3 |
| `ADMIN_ID` | Your Telegram user ID | `987654321` | Step 4 |
| `SESSION_B64` | Encoded session string | `AZN6cF8KjXmP...` | Step 5 |

### Safety Configuration Variables (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFETY_PRESET` | `balanced` | `conservative`, `balanced`, or `aggressive` |
| `MSGS_PER_DAY_LIMIT` | `15000` | Max messages per day (strict!) |
| `ENABLE_SLEEP_SCHEDULE` | `true` | Sleep 11PM-8AM to avoid suspicion |
| `FORWARD_VIA_BOT` | `true` | Forward via Bot API (recommended) |

### Local Testing (.env file)

For local testing, create a `.env` file:

```bash
# Copy the template
cp .env.example .env
```

Edit `.env` with your values:
```bash
# Fill in your actual values
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=7123456789:AAH1234567890abcdefghijklmnop
ADMIN_ID=987654321
SESSION_B64=AZN6cF8KjXmPqRstUvWxYz1234567890abcdefGHIJKLMNOPQRSTUVWXYZ...
SAFETY_PRESET=balanced
```

> ⚠️ **NEVER commit `.env` to Git!** It contains sensitive secrets.
> The `.gitignore` file protects this automatically.

---

## 🚂 Step 7: Deploy to Railway

Railway provides free tier hosting perfect for running your bot 24/7.

### Step 7.1: Create Railway Account

1. Go to: **https://railway.app**
2. Click **"Start for Free"** or **"Get Started"**
3. Sign up using:
   - GitHub (recommended - easiest deployment)
   - Google account
   - Email address

### Step 7.2: Create New Project

1. After logging in, click **"+ New Project"** or **"New"** button
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub (if prompted)
4. Search for: `Forwarder-Bot` or `YatinSharma1303/Forwarder-Bot`
5. Click the repository name
6. Click **"Deploy Now"** or **"Add Service"**

### Step 7.3: Configure Environment Variables

This is where you enter all the values from previous steps:

1. In your Railway project, click on your service (usually named after the repo)
2. Go to **"Variables"** tab (or **"Environment"** → **"Variables"**)
3. Add each variable by clicking **"+ Variable"**:

#### Variable 1: API_ID
```
Name:  API_ID
Value: 12345678
```
(Replace with your actual API_ID from Step 2)

#### Variable 2: API_HASH
```
Name:  API_HASH
Value: abcdef1234567890abcdef1234567890
```
(Replace with your actual API_HASH from Step 2)

#### Variable 3: BOT_TOKEN
```
Name:  BOT_TOKEN
Value: 7123456789:AAH1234567890abcdefghijklmnop
```
(Replace with your actual BOT_TOKEN from Step 3)

#### Variable 4: ADMIN_ID
```
Name:  ADMIN_ID
Value: 987654321
```
(Replace with your actual ADMIN_ID from Step 4)

#### Variable 5: SESSION_B64
```
Name:  SESSION_B64
Value: AZN6cF8KjXmPqRstUvWxYz1234567890abcdefGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789...
```
(Paste the ENTIRE session string from Step 5 - it's long!)

#### Optional: SAFETY_PRESET
```
Name:  SAFETY_PRESET
Value: balanced
```
Options: `conservative` | `balanced` | `aggressive`

### Step 7.4: Configure Persistent Volume (IMPORTANT!)

The session file must persist across restarts. Railway needs a volume:

1. In your service settings, go to **"Storage"** tab
2. Click **"+ New Volume"**
3. Set:
   - **Mount path**: `/app/data`
   - **Size**: `1 GB` (or more for large databases)
4. Click **"Create Volume"**

This ensures your `session.session` file and database survive restarts.

### Step 7.5: Deploy

1. Click **"Deploy"** button (or Railway auto-deploys on push)
2. Wait for build to complete (shows logs):
   ```
   Building Docker image...
   Installing dependencies...
   Starting bot...
   ✅ Bot started successfully!
   ```

3. Once deployed, you'll get a URL like:
   ```
   https://your-forwarder-bot.up.railway.app
   ```
   (This is just the health endpoint - your bot runs in background)

### Step 7.6: Verify Deployment

Check the **Logs** tab in Railway:
```
2024-01-15 10:30:00 INFO Starting Telegram Forwarder Bot...
2024-01-15 10:30:01 INFO Loading safety preset: balanced
2024-01-15 10:30:02 INFO Connecting to Telegram...
2024-01-15 10:30:03 INFO Bot @YatinForwarderBot is online!
2024-01-15 10:30:03 INFO Admin ID: 987654321
2024-01-15 10:30:04 INFO ✅ Bot is ready to receive commands!
```

If you see errors, check the [Troubleshooting](#troubleshooting) section below.

---

## ✅ Step 8: Test Your Bot

### Basic Connection Test

1. Open Telegram
2. Search for your bot: `@YourBotUsername` (from Step 3)
3. Tap **[Start]**
4. Send `/start`

**Expected response:**
```
┌─────────────────────────────────────┐
│  🤖 Telegram Forwarder Bot          │
│  Safety Edition v1.0                │
│                                     │
│  Welcome to your forwarding bot!    │
│                                     │
│  Status: ✅ Running                 │
│  Mode: Balanced                     │
│  Daily limit: 15,000 messages       │
│                                     │
│  Use /help to see all commands      │
└─────────────────────────────────────┘
```

### Test Adding a Source Channel

1. Send `/addsource`
2. Forward a message from the source channel to your bot
3. Bot should confirm:
   ```
   ✅ Source added: @SourceChannelName
   Type: Channel
   Messages available: 15,234
   ```

### Test Adding Destination

1. Send `/adddest`
2. Forward a message from destination channel OR
3. Send the destination channel link/username
4. Bot confirms:
   ```
   ✅ Destination added: @DestinationChannel
   ```

### Test Forwarding (Small Batch First!)

**DO NOT test with 400K messages immediately!** Start small:

1. Send `/forward`
2. Bot asks for limit - enter `10` (test with 10 first)
3. Watch progress:
   ```
   📤 Forwarding: 5/10 (50%)
   Speed: 20 msg/min
   ETA: 15 seconds
   Status: Running
   ```

4. After success, try larger batches: `100`, then `500`, etc.

### Full Command Reference

| Command | Description | Admin Only? |
|---------|-------------|-------------|
| `/start` | Start bot / Show status | No |
| `/help` | Show all commands | No |
| `/addsource` | Add source channel | Yes |
| `/removesource` | Remove source | Yes |
| `/listsources` | List all sources | Yes |
| `/adddest` | Add destination | Yes |
| `/removest` | Remove destination | Yes |
| `/listdests` | List destinations | Yes |
| `/forward` | Start forwarding | Yes |
| `/pause` | Pause operation | Yes |
| `/resume` | Resume paused | Yes |
| `/status` | Current status | Yes |
| `/stats` | Statistics | Yes |
| `/settings` | Change settings | Yes |
| `/resetdaily` | Reset daily counter | Yes |
| `/private` | Add private channel | Yes |
| `/cancel` | Cancel operation | Yes |

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### ❌ Error: `API_ID or API_HASH invalid`

**Cause:** Wrong API credentials  
**Solution:**
1. Revisit [Step 2](#-step-2-get-api_id--api_hash-mytelegramorg)
2. Copy values again from my.telegram.org
3. Ensure no extra spaces or quotes

#### ❌ Error: `BOT_TOKEN invalid`

**Cause:** Wrong bot token  
**Solution:**
1. Message @BotFather with `/token`
2. Select your bot
3. Copy fresh token
4. Update in Railway variables

#### ❌ Error: `Session string needed`

**Cause:** SESSION_B64 not set or invalid  
**Solution:**
1. Re-run `python login_once.py` ([Step 5](#-step-5-generate-session-string-session_b64))
2. Copy new session string
3. Update SESSION_B64 in Railway
4. Redeploy

#### ❌ Error: `The phone number is invalid`

**Cause:** Wrong format in PHONE_NUMBER  
**Solution:** Use format: `+91XXXXXXXXXX` (with + and country code)

#### ❌ Error: `Please wait X minutes before creating another session`

**Cause:** Rate limit from Telegram  
**Solution:** Wait the specified time (usually 5-24 hours), then retry

#### ❌ Error: `CHANNEL_PRIVATE`

**Cause:** Bot can't access private channel  
**Solutions:**
1. Ensure your USER ACCOUNT (not bot) is member of the private channel
2. Use `/private` command with invite link instead of `/addsource`
3. Regenerate session after joining new channels

#### ❌ Bot not responding

**Causes & Solutions:**
1. **Not deployed**: Check Railway dashboard - is service running?
2. **Wrong tokens**: Verify all env vars in Railway
3. **Crashed**: Check Railway Logs tab for errors
4. **Webhook conflict**: If using polling elsewhere, stop it first

#### ❌ `FLOOD_WAIT` error

**Cause:** Too many requests, Telegram rate limited  
**Solutions:**
1. Bot handles this automatically - it will pause and resume
2. If persistent, switch to `conservative` preset
3. Reduce MSGS_PER_DAY_LIMIT in settings

#### ❌ Railway deployment fails

**Common fixes:**
1. Ensure `Dockerfile` exists in repo root
2. Check `Procfile` has correct command
3. Verify Python version compatibility
4. Check build logs for specific error

### Getting Help

If issues persist:

1. **Check Logs**: Railway Logs tab shows real-time errors
2. **Redeploy**: Sometimes "Deploy" → "Redeploy" fixes things
3. **Verify Variables**: Delete and re-add env vars (typos happen!)
4. **Regenerate Session**: Run `login_once.py` again for fresh session

---

## 📊 Safety Presets Explained

Choose based on your urgency vs. risk tolerance:

| Preset | Daily Limit | Time for 400K | Risk Level | Best For |
|--------|-------------|---------------|------------|----------|
| **Conservative** | 8,000/day | 7-10 days | 🟢 Very Low | Old accounts, cautious users |
| **Balanced** | 15,000/day | 4-6 days | 🟡 Medium | Most users (RECOMMENDED) |
| **Aggressive** | 25,000/day | 2-3 days | 🔴 Higher | New accounts willing to risk |

### Changing Preset

In Railway Variables:
```
Name:  SAFETY_PRESET
Value: conservative    (or balanced/aggressive)
```

Or use `/settings` command in bot to change dynamically.

---

## 🎯 Quick Reference Card

### All Values You Need

```
┌────────────────────────────────────────────────────┐
│         YOUR CREDENTIALS CHEAT SHEET               │
├────────────────────────────────────────────────────┤
│                                                    │
│  API_ID:     ______ (numbers only)                 │
│                                                    │
│  API_HASH:   ____________________________________  │
│               (long alphanumeric string)           │
│                                                    │
│  BOT_TOKEN:  ____________________________________  │
│               (numbers:letters_format)             │
│                                                    │
│  ADMIN_ID:   ______ (your user ID number)          │
│                                                    │
│  SESSION_B64: ___________________________________  │
│               ___________________________________  │
│               (very long base64 string)            │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Key URLs

| Resource | URL |
|----------|-----|
| Telegram API | https://my.telegram.org |
| BotFather | t.me/BotFather |
| User Info Bot | t.me/userinfobot |
| Railway Dashboard | https://railway.app/dashboard |
| Repository | https://github.com/YatinSharma1303/Forwarder-Bot |

---

## 🎉 You're Done!

Your Telegram Forwarder Bot is now deployed and ready to forward millions of messages safely!

### What's Next?

1. **Add sources**: Use `/addsource` or `/private` for channels
2. **Add destinations**: Use `/adddest` 
3. **Start forwarding**: Use `/forward` with desired limit
4. **Monitor progress**: Use `/status` and `/stats`
5. **Adjust settings**: Use `/settings` if needed

### Pro Tips

- ✅ Start with small batches (100-500) before going to 400K
- ✅ Monitor `/stats` regularly during bulk operations
- ✅ Let sleep schedule work overnight (suspicious otherwise)
- ✅ Keep session updated if you join new private channels
- ✅ Backup your database occasionally from Railway volume

---

**Built with ❤️ using Telethon + python-telegram-bot**  
**Safety Edition - Designed for 400K+ message operations**

*Last Updated: January 2024*
