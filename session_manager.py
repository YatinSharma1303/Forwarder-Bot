"""
Session Manager Utility for Cloud Deployment
=============================================

This utility helps manage Telethon sessions for cloud deployments.
It can:
- Decode base64-encoded sessions (for env var storage)
- Download sessions from URLs
- Verify session validity

Usage:
    python session_manager.py --decode <base64_string>
    python session_manager.py --verify
    python session_manager.py --encode-file
"""

import os
import sys
import base64
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
SESSION_PATH = os.getenv('SESSION_PATH', 'session.session')
SESSION_B64 = os.getenv('SESSION_B64', '')


async def verify_session():
    """Verify if a session file is valid."""
    print(f"🔍 Verifying session: {SESSION_PATH}")
    
    if not os.path.exists(SESSION_PATH):
        print(f"❌ Session file not found: {SESSION_PATH}")
        return False
    
    if not API_ID or not API_HASH:
        print("❌ API credentials not configured")
        return False
    
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Session is VALID!")
            print(f"   User: {me.first_name} (@{me.username or 'N/A'})")
            print(f"   ID: {me.id}")
            return True
        else:
            print("❌ Session exists but NOT authorized")
            return False
            
    except Exception as e:
        print(f"❌ Session error: {e}")
        return False
    finally:
        await client.disconnect()


def encode_session_to_base64():
    """Encode session file to base64 for environment variable storage."""
    if not os.path.exists(SESSION_PATH):
        print(f"❌ Session file not found: {SESSION_PATH}")
        return None
    
    with open(SESSION_PATH, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    
    print("✅ Session encoded to base64!")
    print(f"\n--- COPY BELOW THIS LINE ---\n{encoded}\n--- COPY ABOVE THIS LINE ---\n")
    print(f"Length: {len(encoded)} characters")
    print("\nAdd this as SESSION_B64 environment variable in Railway")
    
    return encoded


def decode_session_from_base64(b64_string: str):
    """Decode base64 string back to session file."""
    try:
        decoded = base64.b64decode(b64_string)
        
        # Ensure directory exists
        Path(SESSION_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        with open(SESSION_PATH, 'wb') as f:
            f.write(decoded)
        
        print(f"✅ Session decoded and saved to: {SESSION_PATH}")
        print(f"Size: {len(decoded)} bytes")
        return True
        
    except Exception as e:
        print(f"❌ Error decoding: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Session Manager for Forwarder Bot')
    parser.add_argument('--verify', action='store_true', help='Verify session validity')
    parser.add_argument('--encode', action='store_true', help='Encode session to base64')
    parser.add_argument('--decode', type=str, help='Decode base64 string to session file')
    parser.add_argument('--auto-decode', action='store_true', 
                       help='Auto-decode from SESSION_B64 env var')
    
    args = parser.parse_args()
    
    if args.verify:
        asyncio.run(verify_session())
    elif args.encode:
        encode_session_to_base64()
    elif args.decode:
        decode_session_from_base64(args.decode)
    elif args.auto_decode:
        if SESSION_B64:
            decode_session_from_base64(SESSION_B64)
        else:
            print("❌ SESSION_B64 environment variable not set")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
