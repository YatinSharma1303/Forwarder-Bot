"""
First-Time Login Helper for Telegram Forwarder Bot
===================================================

Run this script LOCALLY to authenticate your Telegram account
and create the session file before deploying to Railway/cloud.

Usage:
    python login_once.py

After successful login:
    1. A 'session.session' file will be created
    2. Upload this file to your cloud storage or include in deployment
    3. For Railway: Use a persistent volume or base64 encode it

IMPORTANT: 
    - Run this ONLY ONCE locally
    - Keep your session file SECURE (it contains auth tokens)
    - Never share your session file with anyone!
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PhoneNumberInvalidError

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
SESSION_PATH = os.getenv('SESSION_PATH', 'session.session')


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*60)
    print("🔐 TELEGRAM FORWARDER BOT - First Time Login")
    print("="*60)
    print("\nThis script will:")
    print("  1. Connect to Telegram using your API credentials")
    print("  2. Send a verification code to your phone")
    print("  3. Create a session file for automatic login")
    print("\n⚠️  Your session will be saved to: " + SESSION_PATH)
    print("="*60 + "\n")


async def main():
    """Main login process."""
    print_banner()
    
    # Validate configuration
    if not API_ID or API_ID == 0:
        print("❌ ERROR: API_ID not set!")
        print("   Get it from https://my.telegram.org")
        sys.exit(1)
    
    if not API_HASH:
        print("❌ ERROR: API_HASH not set!")
        print("   Get it from https://my.telegram.org")
        sys.exit(1)
    
    if not PHONE_NUMBER:
        print("❌ ERROR: PHONE_NUMBER not set!")
        print("   Add it to .env file (format: +919876543210)")
        sys.exit(1)
    
    print(f"✅ Configuration loaded:")
    print(f"   API ID: {API_ID}")
    print(f"   Phone: {PHONE_NUMBER}")
    print(f"   Session: {SESSION_PATH}\n")
    
    # Create client
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    
    try:
        # Connect
        print("🔌 Connecting to Telegram...")
        await client.connect()
        
        # Check if already authorized
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"\n✅ Already logged in as: {me.first_name} (@{me.username or 'no username'})")
            print("   Session file is ready for deployment!\n")
            
            # Show session info
            await show_session_info(client)
            return
        
        # Send code request
        print(f"📱 Sending verification code to {PHONE_NUMBER}...")
        
        try:
            result = await client.send_code_request(PHONE_NUMBER)
        except PhoneNumberInvalidError:
            print(f"\n❌ Invalid phone number: {PHONE_NUMBER}")
            print("   Check format: should be like +919876543210")
            sys.exit(1)
        except FloodWaitError as e:
            print(f"\n⏳ Rate limited! Wait {e.seconds} seconds before trying again.")
            sys.exit(1)
        
        print("\n✅ Code sent! Check your Telegram app.")
        
        # Get code from user
        code = input("\nEnter the verification code you received: ").strip()
        
        # Try to sign in
        try:
            me = await client.sign_in(PHONE_NUMBER, code)
        except SessionPasswordNeededError:
            print("\n🔒 Two-factor authentication enabled!")
            password = input("Enter your 2FA password: ").strip()
            me = await client.sign_in(password=password)
        
        # Success!
        print("\n" + "="*60)
        print("✅ LOGIN SUCCESSFUL!")
        print("="*60)
        print(f"\nLogged in as: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username or 'N/A'}")
        print(f"User ID: {me.id}")
        print(f"\nSession saved to: {SESSION_PATH}")
        
        # Show session info
        await show_session_info(client)
        
    except Exception as e:
        print(f"\n❌ Error during login: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        await client.disconnect()
        print("\n👋 Disconnected from Telegram.")


async def show_session_info(client):
    """Show information about the created session."""
    print("\n" + "-"*40)
    print("📁 SESSION FILE INFO")
    print("-"*40)
    
    # Check if session file exists and its size
    if os.path.exists(SESSION_PATH):
        size = os.path.getsize(SESSION_PATH)
        print(f"File: {SESSION_PATH}")
        print(f"Size: {size:,} bytes ({size/1024:.1f} KB)")
        
        # For deployment instructions
        print("\n🚀 DEPLOYMENT INSTRUCTIONS:")
        print("-"*40)
        print("""
For RAILWAY deployment:

Option 1: Base64 Encode (Recommended)
------------------------------------
1. Run this command to encode your session:
   
   base64 session.session > session.txt
   
2. Copy the contents of session.txt

3. In Railway dashboard, add environment variable:
   SESSION_B64=<paste_contents_here>

4. The bot will decode it automatically on startup


Option 2: Persistent Volume
---------------------------
1. Create a volume in Railway dashboard
2. Mount it to /app/data
3. Upload session.session to that volume


Option 3: External Storage
--------------------------
1. Upload session.session to cloud storage (S3, GCS, etc.)
2. Set SESSION_URL environment variable
3. Bot will download on startup


⚠️  IMPORTANT SECURITY NOTES:
-----------------------------
• NEVER commit session.session to Git
• NEVER share your session file
• It contains authentication tokens
• Anyone with it can access your account!
• Keep it secret, keep it safe 🔐
""")
    else:
        print("⚠️ Session file not found!")


if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())
