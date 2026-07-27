"""
Telegram Forwarder Bot - SAFETY EDITION (Anti-Ban Protection)
=============================================================

MAXIMUM PROTECTION for your Telegram account during bulk operations.

Features:
🛡️ Human-like behavior simulation (random delays, patterns)
⏰ Daily/Hourly message limits with auto-pause
📊 Real-time ban-risk assessment
🎲 Anti-detection: Variable timing, natural gaps
🔒 Safety presets: Conservative / Balanced / Aggressive
💤 Sleep scheduling (avoid suspicious overnight activity)
📈 Adaptive speed (slows down if rate limited)

Author: Forwarder-Bot Project | Version: 3.0 (Safety Edition)
"""

import os
import sys
import asyncio
import logging
import sqlite3
import time
import random
import json
import base64
import zipfile
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import traceback

# Environment loading
from dotenv import load_dotenv

# Telethon - For reading source channels (User Session)
from telethon import TelegramClient, events
from telethon.tl.types import (
    Channel,
    Chat,
    Message,
    InputPeerChannel,
    InputPeerChat,
)
from telethon.errors import (
    FloodWaitError,
    SlowModeWaitError,
    ServerError,
    RpcCallFailError,
    RpcMcgetFailError,
    AuthKeyUnregisteredError,
)

# Python Telegram Bot - For control commands & forwarding
from telegram import (
    Update,
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode as TGParseMode
from telegram.error import (
    TelegramError,
    Forbidden,
    RetryAfter,
    NetworkError,
)

# Load environment variables FIRST
load_dotenv()


# ==========================================
# SAFETY CONFIGURATION
# ==========================================

class SafetyPreset(Enum):
    """Safety presets for different risk tolerances."""
    CONSERVATIVE = "conservative"      # Safest, slowest (~7-10 days for 400K)
    BALANCED = "balanced"              # Good balance (~4-6 days for 400K)
    AGGRESSIVE = "aggressive"          # Faster but higher risk (~2-3 days for 400K)
    CUSTOM = "custom"                  # User-defined settings


@dataclass
class SafetyConfig:
    """Safety-focused configuration for anti-ban protection."""
    
    # Basic credentials
    api_id: int = 0
    api_hash: str = ""
    phone_number: str = ""
    bot_token: str = ""
    admin_id: int = 0
    database_path: str = "forwarder_bot.db"
    session_path: str = "session.session"
    log_level: str = "INFO"
    
    # ===== SAFETY PRESET =====
    safety_preset: str = "balanced"  # conservative/balanced/aggressive/custom
    
    # ===== ANTI-BAN: MESSAGE RATE LIMITS =====
    
    # Messages per minute (REALISTIC human speed: 10-30)
    msgs_per_minute_min: int = 15
    msgs_per_minute_max: int = 25
    
    # Messages per hour (Telegram seems OK with ~500-1000/hour)
    msgs_per_hour_limit: int = 800
    
    # Messages per day (STRICT - keep under 20K to be safe)
    msgs_per_day_limit: int = 15000
    
    # ===== HUMAN-LIKE BEHAVIOR =====
    
    # Random pause chance (simulate natural breaks)
    random_pause_chance: float = 0.05  # 5% chance per message
    random_pause_duration_min: int = 30   # 30 seconds
    random_pause_duration_max: int = 300  # 5 minutes
    
    # Reading simulation (pause like a human reading)
    read_simulation_min: float = 1.0   # Min "reading" time (seconds)
    read_simulation_max: float = 3.0   # Max "reading" time (seconds)
    
    # Longer pauses periodically (like taking breaks)
    break_interval_messages: int = 100  # Take a break every N messages
    break_duration_min: int = 60        # 1 minute break
    break_duration_max: int = 180       # 3 minutes break
    
    # ===== SLEEP SCHEDULING (Avoid suspicious overnight activity) =====
    
    enable_sleep_schedule: bool = True
    sleep_start_hour: int = 23     # 11 PM - stop operations
    sleep_end_hour: int = 8        # 8 AM - resume operations
    
    # ===== ADAPTIVE SPEED CONTROL =====
    
    # Slow down factor after rate limit hit (multiply delays by this)
    slowdown_factor_after_flood: float = 2.0
    
    # Maximum slowdown (don't go slower than this)
    max_slowdown_multiplier: float = 5.0
    
    # Gradually restore speed after N successful messages
    recovery_message_count: int = 50
    
    # ===== BATCH PROCESSING =====
    
    batch_size: int = 25  # Smaller batches = more frequent saves + less suspicious
    batch_delay: float = 3.0  # Longer delay between batches
    
    # ===== RETRY LOGIC =====
    
    max_retries: int = 3
    retry_delay_base: float = 10.0  # Longer base delay for safety
    retry_backoff_multiplier: float = 2.0
    
    # ===== AUTO-PAUSE TRIGGERS =====
    
    # Pause after N consecutive errors
    consecutive_error_threshold: int = 3
    
    # How long to auto-pause (seconds)
    auto_pause_duration: int = 120  # 2 minutes
    
    # Pause when approaching hourly/daily limits (% of limit)
    hourly_warning_percent: int = 80   # Pause at 80% of hourly limit
    daily_warning_percent: int = 80    # Pause at 80% of daily limit
    
    # ===== FORWARDING METHOD =====
    
    forward_via_bot: bool = True  # Use bot API (safer - doesn't show your account)
    skip_existing: bool = True
    
    @classmethod
    def from_env(cls) -> 'SafetyConfig':
        """Load configuration from environment variables."""
        preset = os.getenv('SAFETY_PRESET', 'balanced').lower()
        
        # Apply preset defaults first
        config = cls._get_preset_defaults(preset)
        
        # Then override with any custom env vars
        return cls(
            api_id=int(os.getenv('API_ID', config.api_id)),
            api_hash=os.getenv('API_HASH', config.api_hash),
            phone_number=os.getenv('PHONE_NUMBER', config.phone_number),
            bot_token=os.getenv('BOT_TOKEN', config.bot_token),
            admin_id=int(os.getenv('ADMIN_ID', config.admin_id)),
            database_path=os.getenv('DATABASE_PATH', config.database_path),
            session_path=os.getenv('SESSION_PATH', config.session_path),
            log_level=os.getenv('LOG_LEVEL', config.log_level),
            
            # Safety settings
            safety_preset=preset,
            msgs_per_minute_min=int(os.getenv('MSGS_PER_MIN_MIN', config.msgs_per_minute_min)),
            msgs_per_minute_max=int(os.getenv('MSGS_PER_MIN_MAX', config.msgs_per_minute_max)),
            msgs_per_hour_limit=int(os.getenv('MSGS_PER_HOUR_LIMIT', config.msgs_per_hour_limit)),
            msgs_per_day_limit=int(os.getenv('MSGS_PER_DAY_LIMIT', config.msgs_per_day_limit)),
            
            # Human-like behavior
            random_pause_chance=float(os.getenv('RANDOM_PAUSE_CHANCE', config.random_pause_chance)),
            random_pause_duration_min=int(os.getenv('RANDOM_PAUSE_MIN', config.random_pause_duration_min)),
            random_pause_duration_max=int(os.getenv('RANDOM_PAUSE_MAX', config.random_pause_duration_max)),
            read_simulation_min=float(os.getenv('READ_SIM_MIN', config.read_simulation_min)),
            read_simulation_max=float(os.getenv('READ_SIM_MAX', config.read_simulation_max)),
            break_interval_messages=int(os.getenv('BREAK_INTERVAL', config.break_interval_messages)),
            break_duration_min=int(os.getenv('BREAK_DURATION_MIN', config.break_duration_min)),
            break_duration_max=int(os.getenv('BREAK_DURATION_MAX', config.break_duration_max)),
            
            # Sleep schedule
            enable_sleep_schedule=os.getenv('ENABLE_SLEEP_SCHEDULE', str(config.enable_sleep_schedule)).lower() == 'true',
            sleep_start_hour=int(os.getenv('SLEEP_START_HOUR', config.sleep_start_hour)),
            sleep_end_hour=int(os.getenv('SLEEP_END_HOUR', config.sleep_end_hour)),
            
            # Adaptive speed
            slowdown_factor_after_flood=float(os.getenv('SLOWDOWN_FACTOR', config.slowdown_factor_after_flood)),
            max_slowdown_multiplier=float(os.getenv('MAX_SLOWDOWN', config.max_slowdown_multiplier)),
            recovery_message_count=int(os.getenv('RECOVERY_COUNT', config.recovery_message_count)),
            
            # Batch processing
            batch_size=int(os.getenv('BATCH_SIZE', config.batch_size)),
            batch_delay=float(os.getenv('BATCH_DELAY', config.batch_delay)),
            
            # Retry logic
            max_retries=int(os.getenv('MAX_RETRIES', config.max_retries)),
            retry_delay_base=float(os.getenv('RETRY_DELAY_BASE', config.retry_delay_base)),
            retry_backoff_multiplier=float(os.getenv('RETRY_BACKOFF', config.retry_backoff_multiplier)),
            
            # Auto-pause
            consecutive_error_threshold=int(os.getenv('ERROR_THRESHOLD', config.consecutive_error_threshold)),
            auto_pause_duration=int(os.getenv('AUTO_PAUSE_DURATION', config.auto_pause_duration)),
            hourly_warning_percent=int(os.getenv('HOURLY_WARNING', config.hourly_warning_percent)),
            daily_warning_percent=int(os.getenv('DAILY_WARNING', config.daily_warning_percent)),
            
            forward_via_bot=os.getenv('FORWARD_VIA_BOT', str(config.forward_via_bot)).lower() == 'true',
            skip_existing=os.getenv('SKIP_EXISTING', str(config.skip_existing)).lower() == 'true',
        )
    
    @classmethod
    def _get_preset_defaults(cls, preset: str) -> 'SafetyConfig':
        """Get default configuration for a safety preset."""
        if preset == 'conservative':
            return cls(
                safety_preset='conservative',
                msgs_per_minute_min=8,
                msgs_per_minute_max=15,
                msgs_per_hour_limit=500,
                msgs_per_day_limit=10000,
                random_pause_chance=0.10,  # 10% chance
                random_pause_duration_min=60,
                random_pause_duration_max=600,  # Up to 10 min breaks!
                read_simulation_min=2.0,
                read_simulation_max=5.0,
                break_interval_messages=50,
                break_duration_min=120,
                break_duration_max=300,
                batch_size=15,
                batch_delay=5.0,
                max_retries=5,
                retry_delay_base=15.0,
                enable_sleep_schedule=True,
            )
        elif preset == 'aggressive':
            return cls(
                safety_preset='aggressive',
                msgs_per_minute_min=25,
                msgs_per_minute_max=40,
                msgs_per_hour_limit=1500,
                msgs_per_day_limit=25000,
                random_pause_chance=0.02,  # Only 2%
                random_pause_duration_min=15,
                random_pause_duration_max=120,
                read_simulation_min=0.3,
                read_simulation_max=1.0,
                break_interval_messages=200,
                break_duration_min=30,
                break_duration_max=90,
                batch_size=50,
                batch_delay=1.5,
                max_retries=3,
                retry_delay_base=5.0,
                enable_sleep_schedule=False,  # Run 24/7
            )
        else:  # balanced (default)
            return cls(
                safety_preset='balanced',
                msgs_per_minute_min=15,
                msgs_per_minute_max=25,
                msgs_per_hour_limit=800,
                msgs_per_day_limit=15000,
                random_pause_chance=0.05,
                random_pause_duration_min=30,
                random_pause_duration_max=300,
                read_simulation_min=1.0,
                read_simulation_max=3.0,
                break_interval_messages=100,
                break_duration_min=60,
                break_duration_max=180,
                batch_size=25,
                batch_delay=3.0,
                max_retries=3,
                retry_delay_base=10.0,
                enable_sleep_schedule=True,
            )
    
    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []
        if not self.api_id or self.api_id == 0:
            errors.append("API_ID not set")
        if not self.api_hash:
            errors.append("API_HASH not set")
        if not self.phone_number:
            errors.append("PHONE_NUMBER not set")
        if not self.bot_token or self.bot_token == 'YOUR_BOT_TOKEN_HERE':
            errors.append("BOT_TOKEN not set")
        if not self.admin_id or self.admin_id == 0:
            errors.append("ADMIN_ID not set")
        return errors


# Global config
config = SafetyConfig.from_env()

# Configure logging
logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=getattr(logging, config.log_level.upper(), logging.INFO),
)
logger = logging.getLogger('ForwarderBot')


# ==========================================
# DATABASE MANAGER
# ==========================================

class Database:
    """Database manager with rate tracking."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Sources table
        cursor.execute('''CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE NOT NULL,
            access_hash BIGINT,
            channel_title TEXT,
            channel_username TEXT,
            channel_type TEXT DEFAULT 'channel',
            is_private BOOLEAN DEFAULT 0,
            invite_link TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            total_messages INTEGER DEFAULT 0,
            last_message_id INTEGER DEFAULT 0
        )''')
        
        # Destinations table
        cursor.execute('''CREATE TABLE IF NOT EXISTS destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE NOT NULL,
            chat_title TEXT,
            chat_type TEXT DEFAULT 'channel',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )''')
        
        # Forwarded messages
        cursor.execute('''CREATE TABLE IF NOT EXISTS forwarded_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_channel_id INTEGER NOT NULL,
            source_message_id INTEGER NOT NULL,
            dest_chat_id INTEGER NOT NULL,
            dest_message_id INTEGER,
            forwarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            batch_id TEXT,
            UNIQUE(source_channel_id, source_message_id, dest_chat_id)
        )''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_fwd 
            ON forwarded_messages(source_channel_id, source_message_id, dest_chat_id)''')
        
        # Private links
        cursor.execute('''CREATE TABLE IF NOT EXISTS private_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER UNIQUE NOT NULL,
            invite_link TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Rate tracking (NEW!)
        cursor.execute('''CREATE TABLE IF NOT EXISTS rate_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            success BOOLEAN DEFAULT 1,
            details TEXT
        )''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_rate_time 
            ON rate_tracking(timestamp)''')
        
        # Bulk operations
        cursor.execute('''CREATE TABLE IF NOT EXISTS bulk_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT UNIQUE NOT NULL,
            source_channel_id INTEGER NOT NULL,
            dest_chat_id INTEGER NOT NULL,
            status TEXT DEFAULT 'idle',
            total_messages INTEGER DEFAULT 0,
            processed_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            current_message_id INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            config_json TEXT
        )''')
        
        # Settings
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    
    # Source operations
    def add_source(self, **kwargs):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO sources 
                (channel_id, access_hash, channel_title, channel_username, 
                 channel_type, is_private, invite_link, is_active)
                VALUES (:ch_id, :acc_hash, :title, :username, :type, :priv, :link, 1)''', kwargs)
            if kwargs.get('is_private') and kwargs.get('invite_link'):
                cursor.execute('''INSERT OR REPLACE INTO private_links (channel_id, invite_link)
                    VALUES (:ch_id, :link)''', {'ch_id': kwargs['channel_id'], 'link': kwargs['invite_link']})
            conn.commit()
            logger.info(f"📥 Source added: {kwargs.get('channel_title')}")
            return True
        except Exception as e:
            logger.error(f"❌ Error adding source: {e}")
            return False
        finally:
            conn.close()
    
    def remove_source(self, channel_id: int):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sources WHERE channel_id = ?', (channel_id,))
            cursor.execute('DELETE FROM private_links WHERE channel_id = ?', (channel_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_sources(self, active_only=True):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            query = 'SELECT * FROM sources' + (' WHERE is_active=1' if active_only else '') + ' ORDER BY channel_title'
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_source(self, channel_id: int):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sources WHERE channel_id=? AND is_active=1', (channel_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    # Destination operations
    def add_destination(self, chat_id: int, title='', chat_type='channel'):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO destinations (chat_id, chat_title, chat_type, is_active)
                VALUES (?, ?, ?, 1)''', (chat_id, title, chat_type))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Error adding dest: {e}")
            return False
        finally:
            conn.close()
    
    def remove_destination(self, chat_id: int):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM destinations WHERE chat_id = ?', (chat_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_destinations(self, active_only=True):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            query = 'SELECT * FROM destinations' + (' WHERE is_active=1' if active_only else '')
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()
    
    # Forwarded message tracking
    def is_forwarded(self, src_id: int, msg_id: int, dest_id: int) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''SELECT COUNT(*) FROM forwarded_messages 
                WHERE source_channel_id=? AND source_message_id=? AND dest_chat_id=?''',
                (src_id, msg_id, dest_id))
            return cursor.fetchone()[0] > 0
        finally:
            conn.close()
    
    def mark_forwarded_batch(self, entries: List[Tuple]) -> int:
        if not entries:
            return 0
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.executemany('''INSERT OR IGNORE INTO forwarded_messages 
                (source_channel_id, source_message_id, dest_chat_id, dest_message_id, batch_id)
                VALUES (?, ?, ?, ?, ?)''', entries)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"❌ Batch mark error: {e}")
            return 0
        finally:
            conn.close()
    
    # Rate tracking (NEW!)
    def record_action(self, action: str, success: bool = True, details: str = None):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO rate_tracking (action, success, details)
                VALUES (?, ?, ?)''', (action, success, details))
            conn.commit()
        finally:
            conn.close()
    
    def get_action_count_since(self, minutes: int = 60, action: str = None) -> int:
        """Get count of actions in the last N minutes."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(minutes=minutes)
            if action:
                cursor.execute('''SELECT COUNT(*) FROM rate_tracking 
                    WHERE timestamp >= ? AND action=? AND success=1''', (since, action))
            else:
                cursor.execute('''SELECT COUNT(*) FROM rate_tracking 
                    WHERE timestamp >= ? AND success=1''', (since,))
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def cleanup_old_records(self, days: int = 7):
        """Remove records older than N days to keep DB small."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cutoff = datetime.now() - timedelta(days=days)
            cursor.execute('DELETE FROM rate_tracking WHERE timestamp < ?', (cutoff,))
            conn.commit()
        finally:
            conn.close()
    
    # Bulk operations
    def create_bulk_operation(self, op_id: str, src_id: int, dest_id: int, total_msgs: int = 0, config_json: str = None):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR IGNORE INTO bulk_operations 
                (operation_id, source_channel_id, dest_chat_id, status, total_messages, started_at, config_json)
                VALUES (?, ?, ?, 'running', ?, CURRENT_TIMESTAMP, ?)''',
                (op_id, src_id, dest_id, total_msgs, config_json))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Create bulk op error: {e}")
            return False
        finally:
            conn.close()
    
    def update_bulk_operation(self, op_id: str, **kwargs):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            sets = []
            vals = []
            for k, v in kwargs.items():
                sets.append(f"{k} = ?")
                vals.append(v)
            vals.append(op_id)
            cursor.execute(f"UPDATE bulk_operations SET {', '.join(sets)}, last_updated=CURRENT_TIMESTAMP WHERE operation_id=?", vals)
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_bulk_operation(self, op_id: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bulk_operations WHERE operation_id=?', (op_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_active_bulk_operation(self):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''SELECT * FROM bulk_operations 
                WHERE status IN ('running', 'paused') ORDER BY started_at DESC LIMIT 1''')
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    # Private links
    def set_private_link(self, ch_id: int, link: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO private_links (channel_id, invite_link) VALUES (?, ?)''', (ch_id, link))
            cursor.execute("UPDATE sources SET is_private=1, invite_link=? WHERE channel_id=?", (link, ch_id))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_private_link(self, ch_id: int):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT invite_link FROM private_links WHERE channel_id=?', (ch_id,))
            row = cursor.fetchone()
            return row['invite_link'] if row else None
        finally:
            conn.close()


db = Database(config.database_path)


# ==========================================
# SESSION DECODER (for Railway deployment)
# ==========================================

def decode_session_from_env(session_path: str) -> bool:
    """
    Decode session from environment variable (base64 or compressed base64).
    Returns True if session was decoded successfully.
    """
    # Check if session file already exists
    if os.path.exists(session_path):
        size = os.path.getsize(session_path)
        if size > 100:  # Valid session file should be > 100 bytes
            logger.info(f"✅ Session file exists ({size} bytes)")
            return True
    
    # Try SESSION_B64_ZIP (compressed)
    session_b64_zip = os.getenv('SESSION_B64_ZIP', '')
    is_compressed = os.getenv('SESSION_COMPRESSED', 'false').lower() == 'true'
    
    # Try SESSION_B64 (uncompressed)
    session_b64 = os.getenv('SESSION_B64', '')
    
    try:
        if session_b64_zip and is_compressed:
            logger.info("📦 Decoding compressed session (SESSION_B64_ZIP)...")
            # Decode base64
            zip_data = base64.b64decode(session_b64_zip)
            # Decompress zip
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
                # Find session file in zip
                for name in zf.namelist():
                    if 'session' in name.lower():
                        session_data = zf.read(name)
                        break
                else:
                    # Take the first file
                    name = zf.namelist()[0]
                    session_data = zf.read(name)
            
            # Write session file
            with open(session_path, 'wb') as f:
                f.write(session_data)
            
            logger.info(f"✅ Session decompressed and saved ({len(session_data)} bytes)")
            return True
            
        elif session_b64:
            logger.info("🔐 Decoding session (SESSION_B64)...")
            # Decode base64 directly
            session_data = base64.b64decode(session_b64)
            
            # Write session file
            with open(session_path, 'wb') as f:
                f.write(session_data)
            
            logger.info(f"✅ Session decoded and saved ({len(session_data)} bytes)")
            return True
            
        else:
            logger.warning("⚠️ No SESSION_B64 or SESSION_B64_ZIP found in environment")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to decode session: {e}")
        return False


# ==========================================
# TELETHON CLIENT
# ==========================================

class TelethonManager:
    """Telethon client with safety features."""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.is_authorized = False
        self.flood_hits = 0
        self.last_flood_time = 0
        self.current_slowdown = 1.0
    
    async def initialize(self) -> bool:
        if not config.api_id or not config.api_hash:
            logger.error("❌ Telethon credentials missing!")
            return False
        
        try:
            # Decode session from environment variable (for Railway deployment)
            logger.info("🔍 Checking for session file...")
            if not decode_session_from_env(config.session_path):
                logger.error("❌ No valid session found!")
                logger.error("   Add SESSION_B64 or SESSION_B64_ZIP to environment variables")
                return False
            
            self.client = TelegramClient(config.session_path, config.api_id, config.api_hash)
            await self.client.connect()
            self.is_connected = True
            
            self.is_authorized = await self.client.is_user_authorized()
            if not self.is_authorized:
                raise Exception("FIRST_LOGIN_REQUIRED\nRun python login_once.py locally!")
            
            logger.info(f"✅ Telethon connected: {(await self.client.get_me()).first_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Telethon init error: {e}")
            return False
    
    async def get_entity(self, identifier):
        if not self.client or not self.is_connected:
            return None
        try:
            return await self.client.get_entity(identifier)
        except Exception as e:
            logger.error(f"❌ Get entity error: {e}")
            return None
    
    async def iter_messages(self, entity, offset_id=0, reverse=False):
        if not self.client or not self.is_authorized:
            return
        
        try:
            async for msg in self.client.iter_messages(entity, offset_id=offset_id, reverse=reverse):
                yield msg
        except FloodWaitError as e:
            logger.warning(f"⏳ FloodWait while iterating: {e.seconds}s")
            self._record_flood()
            await asyncio.sleep(e.seconds + 1)
            async for msg in self.iter_messages(entity, offset_id, reverse):
                yield msg
        except Exception as e:
            logger.error(f"❌ Iter error: {e}")
    
    async def forward_message(self, entity, message, dest_chat_id: int, bot: Bot = None) -> Optional[int]:
        """Forward with safety delays built-in."""
        try:
            if bot and config.forward_via_bot:
                result = await bot.forward_message(
                    chat_id=dest_chat_id,
                    from_chat_id=self._get_id(entity),
                    message_id=message.id
                )
                return result.message_id
            else:
                result = await message.forward_to(dest_chat_id)
                return result.id
        except Exception as e:
            raise e
    
    def _get_id(self, entity) -> int:
        if hasattr(entity, 'id'):
            return entity.id
        return int(entity) if isinstance(entity, (int, str)) else 0
    
    def _record_flood(self):
        self.flood_hits += 1
        self.last_flood_time = time.time()
        # Increase slowdown
        self.current_slowdown = min(
            self.current_slowdown * config.slowdown_factor_after_flood,
            config.max_slowdown_multiplier
        )
        logger.warning(f"⚠️ Slowdown increased to {self.current_slowdown:.2f}x")
    
    def recover(self):
        """Gradually recover speed after successful operations."""
        self.current_slowdown = max(1.0, self.current_slowdown * 0.9)
    
    def reset_rate_limits(self):
        self.flood_hits = 0
        self.current_slowdown = 1.0
    
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.is_connected = False


telethon_manager = TelethonManager()


# ==========================================
# SAFETY ENGINE (Core Anti-Ban System)
# ==========================================

class SafetyEngine:
    """
    Implements all anti-ban protections:
    - Human-like behavior
    - Rate limiting
    - Sleep scheduling
    - Adaptive speed control
    """
    
    def __init__(self):
        self.messages_this_minute = 0
        self.messages_this_hour = 0
        self.messages_today = 0
        self.minute_start = time.time()
        self.hour_start = time.time()
        self.day_start = time.time()
        self.messages_since_break = 0
        self.messages_since_recovery = 0
        self.current_slowdown = 1.0
        self.is_in_break = False
        self.is_sleeping = False
    
    async def wait_before_message(self, msg_num: int) -> bool:
        """
        Called before each message forward.
        Returns False if should pause/sleep instead.
        """
        # Check sleep schedule
        if config.enable_sleep_schedule and self._should_sleep():
            await self._enter_sleep_mode()
            return False
        
        # Check hourly limit
        if self._approaching_hourly_limit():
            logger.warning("⚠️ Approaching hourly limit!")
            return False
        
        # Check daily limit
        if self._approaching_daily_limit():
            logger.warning("⚠️ Approaching daily limit!")
            return False
        
        # Check if it's time for a break
        if self.messages_since_break >= config.break_interval_messages:
            await self._take_break()
            return False
        
        # Random pause chance
        if random.random() < config.random_pause_chance:
            await self._random_pause()
            return False
        
        # Calculate delay based on current speed
        base_delay = random.uniform(config.read_simulation_min, config.read_simulation_max)
        adjusted_delay = base_delay * self.current_slowdown
        
        # Add small random jitter (±20%)
        jitter = adjusted_delay * random.uniform(-0.2, 0.2)
        final_delay = max(0.1, adjusted_delay + jitter)
        
        logger.debug(f"⏳ Waiting {final_delay:.2f}s before message (slowdown: {self.current_slowdown:.2f}x)")
        await asyncio.sleep(final_delay)
        
        # Track this message
        self._track_message()
        
        return True
    
    async def after_message_success(self):
        """Called after successful message forward."""
        db.record_action('forward', success=True)
        self.messages_since_recovery += 1
        
        # Recovery check
        if self.messages_since_recovery >= config.recovery_message_count:
            self._recover_speed()
    
    async def after_message_failure(self, is_flood: bool = False):
        """Called after failed message forward."""
        db.record_action('forward', success=False, details='flood' if is_flood else 'error')
        
        if is_flood:
            telethon_manager._record_flood()
            self._increase_slowdown()
    
    def _track_message(self):
        """Track message counts for rate limiting."""
        now = time.time()
        self.messages_this_minute += 1
        self.messages_since_break += 1
        
        # Reset minute counter if needed
        if now - self.minute_start >= 60:
            self.messages_this_minute = 0
            self.minute_start = now
        
        # Reset hour counter if needed
        if now - self.hour_start >= 3600:
            self.messages_this_hour = 0
            self.hour_start = now
        
        # Reset day counter if needed
        if now - self.day_start >= 86400:
            self.messages_today = 0
            self.day_start = now
    
    def _should_sleep(self) -> bool:
        """Check if we're in sleep hours."""
        hour = datetime.now().hour
        if config.sleep_start_hour > config.sleep_end_hour:
            # Overnight (e.g., 23:00 to 08:00)
            return hour >= config.sleep_start_hour or hour < config.sleep_end_hour
        else:
            # Daytime nap (unlikely but possible)
            return config.sleep_start_hour <= hour < config.sleep_end_hour
    
    async def _enter_sleep_mode(self):
        """Enter sleep mode until wake time."""
        if self.is_sleeping:
            return
        
        self.is_sleeping = True
        now = datetime.now()
        wake_time = now.replace(hour=config.sleep_end_hour, minute=0, second=0, microsecond=0)
        
        # If wake time is tomorrow
        if now.hour >= config.sleep_start_hour:
            wake_time += timedelta(days=1)
        
        sleep_seconds = (wake_time - now).total_seconds()
        logger.info(f"😴 Entering sleep mode for {sleep_seconds/3600:.1f} hours")
        
        # Notify admin
        await notify_admin(
            f"😴 **SLEEP MODE ACTIVATED**\n\n"
            f"Resuming at {wake_time.strftime('%H:%M')} ({config.sleep_end_hour}:00)\n"
            f"Operations paused until then.\n\n"
            f"This protects your account! 🛡️",
            parse_mode=TGParseMode.MARKDOWN
        )
        
        await asyncio.sleep(sleep_seconds)
        self.is_sleeping = False
        logger.info(f"☀️ Woke up from sleep mode!")
        
        # Reset counters for new day
        self.messages_this_hour = 0
        self.messages_today = 0
        self.hour_start = time.time()
        self.day_start = time.time()
        
        await notify_admin(
            "☀️ **WAKE UP!**\n\nSleep mode ended. Resuming operations...",
            parse_mode=TGParseMode.MARKDOWN
        )
    
    async def _take_break(self):
        """Take a simulated human break."""
        duration = random.uniform(config.break_duration_min, config.break_duration_max)
        logger.info(f"☕ Taking a {duration:.0f}s break (every {config.break_interval_messages} msgs)")
        self.messages_since_break = 0
        self.is_in_break = True
        await asyncio.sleep(duration)
        self.is_in_break = False
    
    async def _random_pause(self):
        """Take a random pause to simulate natural behavior."""
        duration = random.uniform(config.random_pause_duration_min, config.random_pause_duration_max)
        logger.info(f"🎲 Random pause: {duration:.0f}s")
        await asyncio.sleep(duration)
    
    def _approaching_hourly_limit(self) -> bool:
        """Check if approaching hourly limit."""
        threshold = config.msgs_per_hour_limit * (config.hourly_warning_percent / 100)
        return self.messages_this_hour >= threshold
    
    def _approaching_daily_limit(self) -> bool:
        """Check if approaching daily limit."""
        threshold = config.msgs_per_day_limit * (config.daily_warning_percent / 100)
        return self.messages_today >= threshold
    
    def _increase_slowdown(self):
        """Increase slowdown after rate limit."""
        self.current_slowdown = min(
            self.current_slowdown * config.slowdown_factor_after_flood,
            config.max_slowdown_multiplier
        )
        logger.warning(f"⚠️ Speed reduced to {self.current_slowdown:.2f}x")
    
    def _recover_speed(self):
        """Gradually recover speed."""
        old = self.current_slowdown
        self.current_slowdown = max(1.0, self.current_slowdown * 0.9)
        self.messages_since_recovery = 0
        if old != self.current_slowdown:
            logger.info(f"✅ Speed recovering: {old:.2f}x → {self.current_slowdown:.2f}x")
    
    def get_status(self) -> Dict:
        """Get current safety status."""
        return {
            'msgs_this_min': self.messages_this_minute,
            'msgs_this_hour': self.messages_this_hour,
            'msgs_today': self.messages_today,
            'hourly_limit': config.msgs_per_hour_limit,
            'daily_limit': config.msgs_per_day_limit,
            'hourly_pct': (self.messages_this_hour / config.msgs_per_hour_limit * 100) if config.msgs_per_hour_limit > 0 else 0,
            'daily_pct': (self.messages_today / config.msgs_per_day_limit * 100) if config.msgs_per_day_limit > 0 else 0,
            'slowdown': self.current_slowdown,
            'is_sleeping': self.is_sleeping,
            'is_in_break': self.is_in_break,
        }


# Global safety engine
safety_engine = SafetyEngine()


async def notify_admin(text: str, parse_mode=None):
    """Helper to notify admin (will be set after bot init)."""
    # This will be properly connected in main()
    pass


# Operation Status Enum
class OperationStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


# ==========================================
# BULK FORWARDING ENGINE (Safe Edition)
# ==========================================

class SafeBulkEngine:
    """Bulk forwarding engine with full safety integration."""
    
    def __init__(self):
        self.operation_id: Optional[str] = None
        self.status = OperationStatus.IDLE
        self.stats = {
            'total': 0, 'processed': 0, 'success': 0,
            'failed': 0, 'skipped': 0, 'start_time': None, 'batch_num': 0
        }
        self._stop_flag = False
        self._paused = False
        self.bot: Optional[Bot] = None
        self._lock: asyncio.Lock = None
    
    async def start(self, bot: Bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        logger.info("✅ Safe Bulk Engine initialized")
    
    async def stop(self):
        self._stop_flag = True
        self.status = OperationStatus.STOPPED
        if self.operation_id:
            db.update_bulk_operation(self.operation_id, status='stopped')
        logger.info("⏹️ Engine stopped")
    
    async def start_bulk(self, src_id: int, dest_id: int, src_info: Dict, dest_info: Dict,
                         start_from: int = 0) -> str:
        async with self._lock:
            if self.status == OperationStatus.RUNNING:
                raise Exception("Already running!")
            
            op_id = f"safe_{src_id}_{dest_id}_{int(time.time())}"
            self.operation_id = op_id
            self.status = OperationStatus.RUNNING
            self._stop_flag = False
            self._paused = False
            self.stats = {
                'total': 0, 'processed': 0, 'success': 0,
                'failed': 0, 'skipped': 0, 'start_time': datetime.now(), 'batch_num': 0
            }
            
            # Get entity
            entity = await telethon_manager.get_entity(src_id)
            if not entity:
                raise Exception(f"Cannot access source {src_id}")
            
            # Count messages
            total = 0
            try:
                msgs = await telethon_manager.client.get_messages(entity, limit=1)
                total = msgs.total if hasattr(msgs, 'total') else 0
            except:
                pass
            
            db.create_bulk_operation(op_id, src_id, dest_id, total, json.dumps({
                'preset': config.safety_preset,
                'hourly_limit': config.msgs_per_hour_limit,
                'daily_limit': config.msgs_per_day_limit,
            }))
            
            # Notify
            await send_admin_msg(
                f"🛡️ **SAFE BULK START**\n\n"
                f"**Source:** {src_info.get('channel_title', src_id)}\n"
                f"**Dest:** {dest_info.get('chat_title', dest_id)}\n"
                f"**Total:** {total:,}\n"
                f"**Preset:** {config.safety_preset.upper()}\n\n"
                f"**Safety Features Active:**\n"
                f"• ✅ Hourly limit: {config.msgs_per_hour_limit:,}/hr\n"
                f"• ✅ Daily limit: {config.msgs_per_day_limit:,}/day\n"
                f"• ✅ Sleep: {config.sleep_start_hour}:00-{config.sleep_end_hour}:00\n"
                f"• ✅ Human-like delays\n"
                f"• ✅ Auto-pause on rate limits\n\n"
                f"OpID: `{op_id}`",
                parse_mode=TGParseMode.MARKDOWN
            )
            
            # Start background task
            asyncio.create_task(self._execute(op_id, entity, src_id, dest_id, src_info, dest_info, start_from, total))
            
            return op_id
    
    async def _execute(self, op_id, entity, src_id, dest_id, src_info, dest_info, start_from, total):
        try:
            logger.info(f"🚀 Starting safe bulk: {op_id} ({total} msgs)")
            
            batch_entries = []
            consecutive_errors = 0
            msg_count = 0
            
            async for message in telethon_manager.iter_messages(entity, offset_id=start_from, reverse=True):
                # Stop check
                if self._stop_flag:
                    logger.info("⏹️ Stopped by user")
                    db.update_bulk_operation(op_id, status='stopped')
                    await send_admin_msg("⏹️ **STOPPED**", parse_mode=TGParseMode.MARKDOWN)
                    break
                
                # Pause check
                while self._paused:
                    await asyncio.sleep(1)
                
                # Safety check before message
                can_proceed = await safety_engine.wait_before_message(msg_count)
                
                if not can_proceed:
                    # We took a break/pause, continue loop
                    if safety_engine.is_sleeping or safety_engine._approaching_daily_limit():
                        # Serious pause needed
                        db.update_bulk_operation(op_id, status='paused')
                        self._paused = True
                        
                        # Wait until we can proceed
                        while safety_engine.is_sleeping or safety_engine._approaching_daily_limit():
                            await asyncio.sleep(60)  # Check every minute
                        
                        self._paused = False
                        db.update_bulk_operation(op_id, status='running')
                    
                    # After break, re-check this message
                    if config.skip_existing and db.is_forwarded(src_id, message.id, dest_id):
                        self.stats['skipped'] += 1
                        self.stats['processed'] += 1
                        msg_count += 1
                        continue
                
                # Skip if already done
                if config.skip_existing and db.is_forwarded(src_id, message.id, dest_id):
                    self.stats['skipped'] += 1
                    self.stats['processed'] += 1
                    msg_count += 1
                    continue
                
                # Try to forward
                success = False
                for attempt in range(config.max_retries):
                    try:
                        dest_msg_id = await telethon_manager.forward_message(entity, message, dest_id, self.bot)
                        
                        batch_entries.append((src_id, message.id, dest_id, dest_msg_id, op_id))
                        self.stats['success'] += 1
                        success = True
                        consecutive_errors = 0
                        
                        await safety_engine.after_message_success()
                        
                        break
                    
                    except FloodWaitError as e:
                        wait = e.seconds + 1
                        logger.warning(f"⚠️ FloodWait {wait}s (attempt {attempt+1}/{config.max_retries})")
                        
                        await safety_engine.after_message_failure(is_flood=True)
                        
                        if attempt < config.max_retries - 1:
                            # Wait longer than required
                            actual_wait = wait * safety_engine.current_slowdown
                            logger.info(f"⏳ Waiting {actual_wait:.0f}s...")
                            await asyncio.sleep(actual_wait)
                        else:
                            # Last attempt failed, note it
                            logger.error(f"❌ Gave up after {config.max_retries} attempts")
                    
                    except Forbidden as e:
                        logger.error(f"🚫 Forbidden: {e}")
                        await send_admin_msg(
                            f"🚫 **FORBIDDEN ERROR!**\n\nCannot forward to destination.\n"
                            f"Ensure bot is an **admin** there!\n\n{str(e)[:200]}",
                            parse_mode=TGParseMode.MARKDOWN
                        )
                        self._stop_flag = True
                        break
                    
                    except Exception as e:
                        logger.error(f"❌ Error (attempt {attempt+1}): {e}")
                        await safety_engine.after_message_failure()
                        
                        if attempt < config.max_retries - 1:
                            delay = config.retry_delay_base * (config.retry_backoff_multiplier ** attempt)
                            delay *= safety_engine.current_slowdown
                            await asyncio.sleep(delay)
                
                if not success:
                    self.stats['failed'] += 1
                    consecutive_errors += 1
                    
                    if consecutive_errors >= config.consecutive_error_threshold:
                        logger.warning(f"⚠️ Too many errors ({consecutive_errors}), pausing...")
                        self._paused = True
                        db.update_bulk_operation(op_id, status='paused')
                        
                        await send_admin_msg(
                            f"⚠️ **AUTO-PAUSED**\n\n{consecutive_errors} consecutive errors.\n"
                            f"Use `/bulk_resume` to continue.",
                            parse_mode=TGParseMode.MARKDOWN
                        )
                        
                        await asyncio.sleep(config.auto_pause_duration)
                
                self.stats['processed'] += 1
                msg_count += 1
                
                # Batch commit
                if len(batch_entries) >= config.batch_size:
                    db.mark_forwarded_batch(batch_entries)
                    batch_entries.clear()
                    self.stats['batch_num'] += 1
                    
                    db.update_bulk_operation(op_id,
                        processed_count=self.stats['processed'],
                        success_count=self.stats['success'],
                        failed_count=self.stats['failed'],
                        skipped_count=self.stats['skipped'],
                        current_message_id=message.id
                    )
                    
                    # Progress update
                    if msg_count % 100 == 0:
                        await self._send_progress(op_id, total, src_info, dest_info)
                    
                    # Inter-batch delay
                    await asyncio.sleep(config.batch_delay * safety_engine.current_slowdown)
            
            # Final commit
            if batch_entries:
                db.mark_forwarded_batch(batch_entries)
            
            # Complete
            final_status = 'completed' if not self._stop_flag else 'stopped'
            elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
            speed = self.stats['processed'] / elapsed if elapsed > 0 else 0
            
            db.update_bulk_operation(op_id,
                status=final_status,
                processed_count=self.stats['processed'],
                success_count=self.stats['success'],
                failed_count=self.stats['failed'],
                skipped_count=self.stats['skipped'],
                completed_at=datetime.now()
            )
            
            safety_status = safety_engine.get_status()
            
            await send_admin_msg(
                f"{'✅' if final_status=='completed' else '⏹️'} **BULK {'COMPLETE' if final_status=='completed' else 'STOPPED'}!**\n\n"
                f"**Source:** {src_info.get('channel_title', src_id)}\n"
                f"**Dest:** {dest_info.get('chat_title', dest_id)}\n\n"
                f"📊 **Stats:**\n"
                f"• Processed: {self.stats['processed']:,}\n"
                f"• ✅ Success: {self.stats['success']:,}\n"
                f"• ❌ Failed: {self.stats['failed']:,}\n"
                f"• ⏭️ Skipped: {self.stats['skipped']:,}\n\n"
                f"⏱️ Time: {elapsed/60:.1f}min | 🚀 {speed:.1f}msg/s\n\n"
                f"🛡️ **Safety Stats:**\n"
                f"• Today: {safety_status['msgs_today']:,}/{safety_status['daily_limit']:,} ({safety_status['daily_pct']:.1f}%)\n"
                f"• This hour: {safety_status['msgs_this_hour']:,}/{safety_status['hourly_limit']:,}\n"
                f"• Final slowdown: {safety_status['slowdown']:.2f}x\n\n"
                f"OpID: `{op_id}`",
                parse_mode=TGParseMode.MARKDOWN
            )
            
            self.status = OperationStatus.IDLE if final_status == 'completed' else OperationStatus.STOPPED
            logger.info(f"✅ Bulk complete: {self.stats['processed']} processed")
            
        except Exception as e:
            logger.error(f"❌ Bulk error: {e}\n{traceback.format_exc()}")
            db.update_bulk_operation(op_id, status='error', error_message=str(e)[:500])
            await send_admin_msg(
                f"❌ **BULK FAILED!**\n\n{str(e)[:300]}\n\nUse `/bulk_resume` to retry.",
                parse_mode=TGParseMode.MARKDOWN
            )
            self.status = OperationStatus.ERROR
    
    async def _send_progress(self, op_id, total, src_info, dest_info):
        if not self.bot:
            return
        
        s = safety_engine.get_status()
        pct = (self.stats['processed'] / total * 100) if total > 0 else 0
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        speed = self.stats['processed'] / elapsed if elapsed > 0 else 0
        eta = (total - self.stats['processed']) / speed if speed > 0 else 0
        
        bar_len = 20
        filled = int(bar_len * pct / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        
        try:
            await self.bot.send_message(
                chat_id=config.admin_id,
                text=f"""📊 **SAFE BULK PROGRESS**

**Source:** {src_info.get('channel_title')}
**Dest:** {dest_info.get('chat_title')}

`{bar}` **{pct:.1f}%**

📈 **Processed:** {self.stats['processed']:,} / **{total:,}**
✅ {self.stats['success']:,} | ❌ {self.stats['failed']:,} | ⏭️ {self.stats['skipped']:,}

⏱️ {speed:.0f}/s | ETA: {eta/60:.1f}min | 📦 {self.stats['batch_num']:,_}

🛡️ **Safety:**
Hour: {s['msgs_this_hour']:,}/{s['hourly_limit']:,} ({s['hourly_pct']:.0f}%)
Day: {s['msgs_today']:,}/{s['daily_limit']:,} ({s['daily_pct']:.0f}%)
Speed: {s['slowdown']:.2f}x {'😴' if s['is_sleeping'] else ''}

_OpID: `{op_id}`_""",
                parse_mode=TGParseMode.MARKDOWN
            )
        except Exception as e:
            logger.debug(f"Progress msg failed: {e}")
    
    async def pause(self):
        self._paused = True
        self.status = OperationStatus.PAUSED
        if self.operation_id:
            db.update_bulk_operation(self.operation_id, status='paused')
        logger.info(f"⏸️ Paused {self.operation_id}")
    
    async def resume(self):
        self._paused = False
        self.status = OperationStatus.RUNNING
        if self.operation_id:
            db.update_bulk_operation(self.operation_id, status='running')
        telethon_manager.reset_rate_limits()
        logger.info(f"▶️ Resumed {self.operation_id}")


safe_engine = SafeBulkEngine()


# Helper for sending admin messages
async def send_admin_msg(text: str, parse_mode=None):
    if safe_engine.bot:
        try:
            await safe_engine.bot.send_message(chat_id=config.admin_id, text=text, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Admin msg failed: {e}")


# ==========================================
# COMMAND HANDLERS
# ==========================================

def _is_admin(uid: int) -> bool:
    return uid == config.admin_id


async def cmd_start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        f"""🤖 **Telegram Forwarder Bot**
*🛡️ Safety Edition - Account Protection MAXIMIZED*

Welcome {update.effective_user.first_name}! 👋

**🛡️ Safety Features:**
• ✅ Human-like behavior simulation
• ⏰ Automatic sleep schedule (11PM-8AM)
• 📊 Hourly/Daily message limits
• 🎲 Random breaks & pauses
• 🐢 Adaptive speed (auto-slow on limits)
• 💾 Crash-safe resume capability

**📋 Commands:**
`/help` - Full guide
`/status` - System + safety status
`/safety_status` - Detailed safety metrics
`/bulk_start <src> <dest>` - Start forwarding!

**⚙️ Current Preset:** *{config.safety_preset.upper()}*
*Change with SAFETY_PRESET in .env*

*Your account is PROTECTED* 🛡️""",
        parse_mode=TGParseMode.MARKDOWN
    )


async def cmd_help(update: Update, context: CallbackContext):
    await update.message.reply_text("""📖 **Complete Help**

**📥 SOURCES** (Read FROM here)
• `/addsource @user` - Public channel
• `/addsource <id>` - By ID
• `/addsource_private <link>` - Private via link
• `/sources` - List sources
• `/mysources` - Browse your channels

**📤 DESTINATIONS** (Forward TO here)
• `/adddest @user_or_id` - Add destination
• `/dests` - List destinations

**🚀 BULK OPERATIONS**
• `/bulk_start <src_id> <dest_id>` - START!
• `/bulk_status` - Progress
• `/bulk_pause` - Pause
• `/bulk_resume` - Resume
• `/bulk_stop` - Stop

**🛡️ SAFETY**
• `/safety_status` - Detailed safety metrics
• `/status` - Overview

**💡 TIPS FOR 400K+:**
1. Use `conservative` preset for maximum safety
2. Let it run 24/7 with sleep schedule ON
3. Monitor with `/safety_status`
4. Don't worry about crashes - auto-resumes!""", parse_mode=TGParseMode.MARKDOWN)


async def cmd_safety_status(update: Update, context: CallbackContext):
    """Detailed safety metrics."""
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    
    s = safety_engine.get_status()
    active_op = db.get_active_bulk_operation()
    
    text = f"""🛡️ **SAFETY DASHBOARD**

**⚙️ Configuration:**
• Preset: *{config.safety_preset.upper()}*
• Hourly Limit: {config.msgs_per_hour_limit:,}
• Daily Limit: {config.msgs_per_day_limit:,}
• Sleep: {config.sleep_start_hour}:00-{config.sleep_end_hour}:00 {'✅' if config.enable_sleep_schedule else '❌'}

**📊 Current Usage:**
• This Minute: {s['msgs_this_min']}
• This Hour: {s['msgs_this_hour']:,} / {s['hourly_limit']:,} (**{s['hourly_pct']:.1f}%**)
• Today: {s['msgs_today']:,} / {s['daily_limit']:,} (**{s['daily_pct']:.1f}%**)

**🐢 Speed Control:**
• Current Slowdown: {s['slowdown']:.2f}x
• Is Sleeping: {'Yes 😴' if s['is_sleeping'] else 'No'}
• In Break: {'Yes ☕' if s['is_in_break'] else 'No'}

---
"""
    
    if active_op:
        op = active_op
        text += f"""**🔄 Active Operation:**
• Status: {op['status'].upper()}
• Processed: {op['processed_count']:,} / {op['total_messages']:,}
• ✅ {op['success_count']:,} | ❌ {op['failed_count']:,} | ⏭️ {op['skipped_count']:,}
"""
    else:
        text += "No active operation."
    
    # Risk assessment
    risk_level = "🟢 LOW"
    if s['daily_pct'] > 90 or s['hourly_pct'] > 90:
        risk_level = "🔴 HIGH"
    elif s['daily_pct'] > 70 or s['hourly_pct'] > 70:
        risk_level = "🟡 MEDIUM"
    
    text += f"\n**⚠️ Ban Risk Level: {risk_level}**"
    
    await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN)


async def cmd_status(update: Update, context: CallbackContext):
    """System status overview."""
    sources = db.get_sources()
    dests = db.get_destinations()
    active_op = db.get_active_bulk_operation()
    s = safety_engine.get_status()
    
    text = f"""📊 **SYSTEM STATUS**

**🔌 Telethon:** {'✅' if telethon_manager.is_connected else '❌'}
**🔐 Authorized:** {'✅' if telethon_manager.is_authorized else '❌'}
**🤖 Bot:** ✅ Online
**⚙️ Engine:** {safe_engine.status.value.upper()}
**🛡️ Safety:** {config.safety_preset.upper()}

**📥 Sources:** {len(sources)}
**📤 Destinations:** {len(dests)}

**📊 Usage Today:**
Hour: {s['msgs_this_hour']:,}/{s['hourly_limit']:,} ({s['hourly_pct']:.0f}%)
Day: {s['msgs_today']:,}/{s['daily_limit']:,} ({s['daily_pct']:.0f}%)
"""
    
    if active_op:
        op = active_op
        pct = (op['processed_count']/op['total_messages']*100) if op['total_messages'] > 0 else 0
        text += f"""
**🔄 Active Op:**
`{op['operation_id'][:20]}...`
{op['status'].upper()} | {pct:.1f}%
{op['processed_count']:,} processed | ✅{op['success_count']:,} ❌{op['failed_count']:,}
"""
    
    await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN)


# Source commands
async def cmd_add_source(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/addsource <@username_or_id>`", parse_mode=TGParseMode.MARKDOWN); return
    
    identifier = context.args[0].strip()
    if identifier.startswith('@'): identifier = identifier[1:]
    if identifier.startswith('https://t.me/'): identifier = identifier.replace('https://t.me/', '')
    
    await update.message.reply_text(f"🔍 Looking up `{identifier}`...", parse_mode=TGParseMode.MARKDOWN)
    
    try:
        entity = await telethon_manager.get_entity(identifier)
        if not entity:
            await update.message.reply_text("❌ Not found. Use `/addsource_private <link>` for private.", parse_mode=TGParseMode.MARKDOWN); return
        
        ch_id = entity.id
        acc_hash = getattr(entity, 'access_hash', None)
        title = getattr(entity, 'title', '') or getattr(entity, 'first_name', '') or 'Unknown'
        username = getattr(entity, 'username', '') or ''
        is_private = not bool(username)
        
        db.add_source(channel_id=ch_id, access_hash=acc_hash, title=title, username=username, channel_type='channel', is_private=is_private)
        
        total = 0
        try:
            msgs = await telethon_manager.client.get_messages(entity, limit=1)
            total = msgs.total if hasattr(msgs, 'total') else 0
        except: pass
        
        await update.message.reply_text(
            f"""✅ **Source Added!**

**Name:** {title}
**ID:** `{ch_id}`
**Messages:** {total:,}
**Privacy:** {'🔒 Private' if is_private else '🌐 Public'}

⏱️ **Estimated Time (at current preset):**
• Conservative: ~{total//200:,}h | Balanced: ~{total//500:,}h | Aggressive: ~{total//1000:,}h

*Use `/bulk_start {ch_id} <dest_id>` to start*""", parse_mode=TGParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}", parse_mode=TGParseMode.MARKDOWN)


async def cmd_add_source_private(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/addsource_private <invite_link>`", parse_mode=TGParseMode.MARKDOWN); return
    
    link = context.args[0]
    if not link.startswith('http'): link = f"https://t.me/{link}"
    
    await update.message.reply_text("🔍 Accessing...", parse_mode=TGParseMode.MARKDOWN)
    
    try:
        entity = await telethon_manager.get_entity(link)
        if entity:
            ch_id = entity.id
            title = getattr(entity, 'title', '') or 'Private'
            db.add_source(channel_id=ch_id, access_hash=None, title=title, username='', channel_type='channel', is_private=True, invite_link=link)
            await update.message.reply_text(f"✅ **Private Added!**\n\n**{title}**\nID: `{ch_id}`", parse_mode=TGParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ Saved but couldn't resolve yet.", parse_mode=TGParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}", parse_mode=TGParseMode.MARKDOWN)


async def cmd_remove_source(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if not context.args:
        sources = db.get_sources()
        if not sources: await update.message.reply_text("No sources."); return
        text = "📋 **Sources:**\n\n" + "\n".join(f"`{s['channel_id']}` - {s['channel_title']}" for s in sources)
        text += "\n\nUse: `/removesource <id>`"
        await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN); return
    
    try:
        ch_id = int(context.args[0])
        if db.remove_source(ch_id):
            await update.message.reply_text(f"✅ Removed `{ch_id}`.", parse_mode=TGParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Not found.", parse_mode=TGParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid ID.", parse_mode=TGParseMode.MARKDOWN)


async def cmd_list_sources(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    sources = db.get_sources()
    if not sources:
        await update.message.reply_text("📭 No sources. Use `/addsource`", parse_mode=TGParseMode.MARKDOWN); return
    
    text = f"📥 **Sources** ({len(sources)})\n\n"
    for i, s in enumerate(sources, 1):
        icon = "🔒" if s['is_private'] else "🌐"
        text += f"{i}. {icon} **{s['channel_title']}**\n   `{s['channel_id']}` | {s.get('total_messages','?'):,} msgs\n\n"
    await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN)


async def cmd_my_sources(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    await update.message.reply_text("🔄 Fetching...", parse_mode=TGParseMode.MARKDOWN)
    
    try:
        dialogs = await telethon_manager.client.get_dialogs(limit=None)
        channels = []
        for d in dialogs:
            e = d.entity
            if isinstance(e, Channel) and (e.broadcast or e.megagroup):
                channels.append({'id': e.id, 'title': getattr(e, 'title', 'Unknown'), 'username': getattr(e, 'username', ''), 'is_private': not bool(getattr(e, 'username', ''))})
        
        if not channels:
            await update.message.reply_text("📭 No channels found."); return
        
        text = f"📋 **Your Channels** ({len(channels)})\n\n"
        for i, c in enumerate(channels[:25], 1):
            icon = "🔒" if c['is_private'] else "🌐"
            text += f"{i}. {icon} **{c['title']}**\n   `{c['id']}`\n\n"
        await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode=TGParseMode.MARKDOWN)


# Destination commands
async def cmd_add_destination(update: Update, context: CallbackContext):
    try:
        if not _is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Not authorized."); return
        
        # Method 1: Forwarded message (most reliable!)
        forward_from_chat = getattr(update.message, 'forward_from_chat', None)
        if forward_from_chat:
            try:
                chat = forward_from_chat
                chat_id = chat.id
                chat_title = chat.title or 'Unknown Channel'
                chat_type = str(chat.type) if hasattr(chat.type, '__str__') else 'channel'
                
                db.add_destination(chat_id, chat_title, chat_type)
                
                await update.message.reply_text(
                    f"✅ **Destination Added!**\n\n"
                    f"**{chat_title}**\n"
                    f"ID: `{chat_id}`\n"
                    f"Type: {chat_type}\n\n"
                    f"_Added via forwarded message_ ✨",
                    parse_mode=TGParseMode.MARKDOWN
                )
                return
            except Exception as e:
                logger.error(f"adddest forward method error: {e}")
                await update.message.reply_text(f"❌ Error processing forward: {str(e)[:200]}", parse_mode=TGParseMode.MARKDOWN)
                return
        
        # Method 2: Reply to a message from destination channel
        reply_msg = getattr(update.message, 'reply_to_message', None)
        reply_forward = getattr(reply_msg, 'forward_from_chat', None) if reply_msg else None
        if reply_msg and reply_forward:
            try:
                chat = reply_forward
                chat_id = chat.id
                chat_title = chat.title or 'Unknown Channel'
                chat_type = str(chat.type) if hasattr(chat.type, '__str__') else 'channel'
                
                db.add_destination(chat_id, chat_title, chat_type)
                
                await update.message.reply_text(
                    f"✅ **Destination Added!**\n\n"
                    f"**{chat_title}**\n"
                    f"ID: `{chat_id}`\n"
                    f"Type: {chat_type}\n\n"
                    f"_Added via replied message_ ✨",
                    parse_mode=TGParseMode.MARKDOWN
                )
                return
            except Exception as e:
                logger.error(f"adddest reply method error: {e}")
                await update.message.reply_text(f"❌ Error: {str(e)[:200]}", parse_mode=TGParseMode.MARKDOWN)
                return
        
        # Method 3: Username or ID (traditional method)
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage Options:**\n\n"
                "**Method 1 - Forward Message (Recommended):**\n"
                "Forward ANY message from the destination channel to me\n\n"
                "**Method 2 - Username/ID:**\n"
                "`/adddest @username`\n"
                "`/adddest <chat_id>`\n\n"
                "⚠️ Bot must be admin in destination channel!",
                parse_mode=TGParseMode.MARKDOWN
            )
            return
        
        identifier = context.args[0].strip()
        if identifier.startswith('@'): identifier = identifier[1:]
        
        try:
            chat = await context.bot.get_chat(identifier)
            db.add_destination(chat.id, chat.title or '', chat.type.value if hasattr(chat.type, 'value') else str(chat.type))
            await update.message.reply_text(f"✅ **Destination Added!**\n\n**{chat.title}**\nID: `{chat.id}`", parse_mode=TGParseMode.MARKDOWN)
        except Exception as e:
            error_msg = str(e)[:200]
            logger.error(f"adddest username/id error: {error_msg}")
            
            # Provide helpful suggestions based on error
            if 'not found' in error_msg.lower() or 'chat' in error_msg.lower():
                suggestion = (
                    "💡 **Try this instead:**\n\n"
                    "1. Go to your **destination channel**\n"
                    "2. **Forward any message** from that channel\n"
                    "3. Send it to me with `/adddest`\n\n"
                    "Or make sure:\n"
                    "• Bot is **admin** in the channel\n"
                    "• Bot has **Post Messages** permission\n"
                    "• Channel is public or bot is member"
                )
            else:
                suggestion = f"Error: {error_msg}\n\nBot must be admin!"
            
            await update.message.reply_text(f"❌ {suggestion}", parse_mode=TGParseMode.MARKDOWN)
    
    except Exception as e:
        logger.error(f"CRITICAL adddest error: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Unexpected error: {str(e)[:200]}", parse_mode=TGParseMode.MARKDOWN)


async def cmd_remove_destination(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if not context.args:
        dests = db.get_destinations()
        if not dests: await update.message.reply_text("No destinations."); return
        text = "📋 **Destinations:**\n\n" + "\n".join(f"`{d['chat_id']}` - {d['chat_title']}" for d in dests)
        text += "\n\nUse: `/removedest <id>`"
        await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN); return
    
    try:
        ch_id = int(context.args[0])
        if db.remove_destination(ch_id):
            await update.message.reply_text(f"✅ Removed `{ch_id}`.", parse_mode=TGParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Not found.", parse_mode=TGParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid ID.", parse_mode=TGParseMode.MARKDOWN)


async def cmd_list_destinations(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    dests = db.get_destinations()
    if not dests:
        await update.message.reply_text("📭 No destinations. Use `/adddest`", parse_mode=TGParseMode.MARKDOWN); return
    
    text = f"📤 **Destinations** ({len(dests)})\n\n"
    for i, d in enumerate(dests, 1):
        text += f"{i}. **{d['chat_title']}**\n   `{d['chat_id']}`\n\n"
    await update.message.reply_text(text, parse_mode=TGParseMode.MARKDOWN)


# Bulk commands
async def cmd_bulk_start(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if len(context.args) < 2:
        sources = db.get_sources()
        dests = db.get_destinations()
        
        help_text = "❌ Usage: `/bulk_start <source_id> <dest_id>`\n\n**Sources:**\n"
        if sources:
            for s in sources[:10]:
                help_text += f"• `{s['channel_id']}` - {s['channel_title']} ({s.get('total_messages','?'):,})\n"
        help_text += f"\n**Destinations:**\n"
        if dests:
            for d in dests[:10]:
                help_text += f"• `{d['chat_id']}` - {d['chat_title']}\n"
        help_text += "\nExample: `/bulk_start -100123 -100456`"
        await update.message.reply_text(help_text, parse_mode=TGParseMode.MARKDOWN); return
    
    try:
        src_id = int(context.args[0])
        dest_id = int(context.args[1])
        
        src_info = db.get_source(src_id)
        if not src_info:
            await update.message.reply_text(f"❌ Source `{src_id}` not found.", parse_mode=TGParseMode.MARKDOWN); return
        
        dests = db.get_destinations()
        dest_info = next((d for d in dests if d['chat_id'] == dest_id), None)
        if not dest_info:
            await update.message.reply_text(f"❌ Destination `{dest_id}` not found.", parse_mode=TGParseMode.MARKDOWN); return
        
        if safe_engine.status == OperationStatus.RUNNING:
            await update.message.reply_text("⚠️ Already running! Use `/bulk_stop` first.", parse_mode=TGParseMode.MARKDOWN); return
        
        await update.message.reply_text(
            f"🚀 **Starting SAFE Bulk Forward...**\n\n"
            f"From: {src_info['channel_title']}\nTo: {dest_info['chat_title']}\n\n"
            f"🛡️ Safety: {config.safety_preset.upper()}\n"
            f"Limits: {config.msgs_per_hour_limit:,}/hr | {config.msgs_per_day_limit:,}/day\n"
            f"Sleep: {config.sleep_start_hour}:00-{config.sleep_end_hour}:00\n\n"
            f"⏳ Initializing...",
            parse_mode=TGParseMode.MARKDOWN
        )
        
        start_from = src_info.get('last_message_id', 0)
        op_id = await safe_engine.start_bulk(src_id, dest_id, src_info, dest_info, start_from)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid IDs.", parse_mode=TGParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:300]}", parse_mode=TGParseMode.MARKDOWN)


async def cmd_bulk_status(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    op = db.get_active_bulk_operation()
    if not op:
        await update.message.reply_text("📭 No active ops. Start with `/bulk_start`", parse_mode=TGParseMode.MARKDOWN); return
    
    s = safety_engine.get_status()
    pct = (op['processed_count']/op['total_messages']*100) if op['total_messages'] > 0 else 0
    
    bar_len = 20
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    
    elapsed_str = ""
    if op.get('started_at'):
        try:
            started = datetime.fromisoformat(op['started_at'])
            elapsed = (datetime.now() - started).total_seconds()
            elapsed_str = f"{elapsed/60:.1f}min"
            if elapsed > 0:
                speed = op['processed_count'] / elapsed
                eta = (op['total_messages'] - op['processed_count']) / speed if speed > 0 else 0
                elapsed_str += f" | {speed:.0f}/s | ETA: {eta/60:.1f}min"
        except: pass
    
    await update.message.reply_text(
        f"""📊 **BULK STATUS**

**Status:** {op['status'].upper()}
**OpID:** `{op['operation_id'][:30]}`

`{bar}` **{pct:.2f}%**

📈 **{op['processed_count']:,}** / **{op['total_messages']:,}**
✅ {op['success_count']:,} | ❌ {op['failed_count']:,} | ⏭️ {op['skipped_count']:,}

⏱️ {elapsed_str or 'N/A'}

🛡️ **Safety:**
Day: {s['msgs_today']:,}/{s['daily_limit']:,} ({s['daily_pct']:.0f}%)
Speed: {s['slowdown']:.2f}x

---
`/bulk_pause` | `/bulk_resume` | `/bulk_stop`""",
        parse_mode=TGParseMode.MARKDOWN
    )


async def cmd_bulk_pause(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if safe_engine.status != OperationStatus.RUNNING:
        await update.message.reply_text("⚠️ Nothing running to pause.", parse_mode=TGParseMode.MARKDOWN); return
    
    await safe_engine.pause()
    await update.message.reply_text("⏸️ **PAUSED**\n\nProgress saved. Use `/bulk_resume`.", parse_mode=TGParseMode.MARKDOWN)


async def cmd_bulk_resume(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if safe_engine.status == OperationStatus.PAUSED:
        await safe_engine.resume()
        await update.message.reply_text("▶️ **RESUMED!**\n\nContinuing from where we left off...", parse_mode=TGParseMode.MARKDOWN)
    else:
        active_op = db.get_active_bulk_operation()
        if active_op and active_op['status'] == 'paused':
            await safe_engine.resume()
            await update.message.reply_text("▶️ **Resuming...**", parse_mode=TGParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ Nothing paused. Start new with `/bulk_start`", parse_mode=TGParseMode.MARKDOWN)


async def cmd_bulk_stop(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if safe_engine.status not in [OperationStatus.RUNNING, OperationStatus.PAUSED]:
        await update.message.reply_text("⚠️ No active operation.", parse_mode=TGParseMode.MARKDOWN); return
    
    await safe_engine.stop()
    await update.message.reply_text("⏹️ **STOPPED**\n\nProgress saved. Resume anytime with `/bulk_resume`", parse_mode=TGParseMode.MARKDOWN)


async def cmd_set_link(update: Update, context: CallbackContext):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized."); return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/setlink <id> <link>`", parse_mode=TGParseMode.MARKDOWN); return
    
    try:
        ch_id = int(context.args[0])
        link = context.args[1]
        src = db.get_source(ch_id)
        if not src:
            await update.message.reply_text(f"❌ Source `{ch_id}` not found.", parse_mode=TGParseMode.MARKDOWN); return
        
        db.set_private_link(ch_id, link)
        await update.message.reply_text(f"✅ **Link Set!**\n\n**{src['channel_title']}**\n{link}", parse_mode=TGParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Invalid ID.", parse_mode=TGParseMode.MARKDOWN)


# ==========================================
# MAIN APPLICATION
# ==========================================

# Global flag for health check
bot_ready = False

async def post_init(app: Application):
    global bot_ready
    logger.info("🚀 Initializing...")
    ok = await telethon_manager.initialize()
    if not ok:
        logger.error("❌ Telethon failed!"); return
    await safe_engine.start(app.bot)
    bot_ready = True
    logger.info("✅ Ready!")


async def post_shutdown(app: Application):
    global bot_ready
    logger.info("🛑 Shutting down...")
    bot_ready = False
    await safe_engine.stop()
    await telethon_manager.disconnect()
    logger.info("👋 Done.")


def main():
    global bot_ready
    
    errors = config.validate()
    if errors:
        print("\n❌ Config Errors:")
        for e in errors:
            print(f"  • {e}")
        print("\nFix .env file"); return
    
    app = Application.builder().token(config.bot_token).post_init(post_init).post_shutdown(post_shutdown).build()
    
    # Register all command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("safety_status", cmd_safety_status))
    app.add_handler(CommandHandler("addsource", cmd_add_source))
    app.add_handler(CommandHandler("addsource_private", cmd_add_source_private))
    app.add_handler(CommandHandler("removesource", cmd_remove_source))
    app.add_handler(CommandHandler("sources", cmd_list_sources))
    app.add_handler(CommandHandler("mysources", cmd_my_sources))
    app.add_handler(CommandHandler("adddest", cmd_add_destination))
    app.add_handler(CommandHandler("removedest", cmd_remove_destination))
    app.add_handler(CommandHandler("dests", cmd_list_destinations))
    app.add_handler(CommandHandler("bulk_start", cmd_bulk_start))
    app.add_handler(CommandHandler("bulk_status", cmd_bulk_status))
    app.add_handler(CommandHandler("bulk_pause", cmd_bulk_pause))
    app.add_handler(CommandHandler("bulk_resume", cmd_bulk_resume))
    app.add_handler(CommandHandler("bulk_stop", cmd_bulk_stop))
    app.add_handler(CommandHandler("setlink", cmd_set_link))
    
    logger.info("="*60)
    logger.info("🤖 FORWARDER BOT - SAFETY EDITION")
    logger.info("="*60)
    logger.info(f"Preset: {config.safety_preset}")
    logger.info(f"Limits: {config.msgs_per_hour_limit}/hr, {config.msgs_per_day_limit}/day")
    logger.info(f"Sleep: {config.sleep_start_hour}-{config.sleep_end_hour}")
    logger.info("="*60)
    
    print("\n" + "🛡️"*20)
    print("\n🤖 Telegram Forwarder Bot - SAFETY EDITION")
    print("   Maximum Account Protection!\n")
    print("="*60)
    print(f"\n🛡️ Safety Configuration:")
    print(f"   • Preset: {config.safety_preset.upper()}")
    print(f"   • Hourly Limit: {config.msgs_per_hour_limit:,}")
    print(f"   • Daily Limit: {config.msgs_per_day_limit:,}")
    print(f"   • Sleep Schedule: {config.sleep_start_hour}:00 - {config.sleep_end_hour}:00")
    print(f"   • Human Delays: {config.read_simulation_min}-{config.read_simulation_max}s")
    print(f"   • Break Every: {config.break_interval_messages} msgs")
    print("="*60 + "\n")
    
    # Start HTTP health check server for Railway
    from aiohttp import web as aiohttp_web
    
    async def health_check(request):
        if bot_ready and telethon_manager.is_authorized:
            return aiohttp_web.json_response({
                "status": "ok",
                "bot": "online",
                "telethon": "connected",
                "engine": safe_engine.status.value if safe_engine else "unknown"
            })
        else:
            return aiohttp_web.json_response(
                {"status": "not_ready"}, 
                status=503
            )
    
    async def start_http_server():
        http_app = aiohttp_web.Application()
        http_app.router.add_get('/health', health_check)
        http_app.router.add_get('/', health_check)  # Root also works
        
        runner = aiohttp_web.AppRunner(http_app)
        await runner.setup()
        
        port = int(os.getenv('PORT', 8080))
        site = aiohttp_web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 Health check server running on port {port}")
    
    # Start both HTTP server and Telegram polling
    import asyncio
    
    async def run_all():
        # Start HTTP server first (for Railway health checks)
        await start_http_server()
        
        logger.info("🚀 Starting Telegram polling...")
        
        # Initialize and start polling properly
        await app.initialize()
        await post_init(app)
        
        # Start the updater with polling - THIS IS WHAT WAS MISSING!
        await app.updater.start_polling(drop_pending_updates=True)
        await app.start()
        
        logger.info("✅ Bot is running with polling and health endpoint!")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)  # Keep alive
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            await post_shutdown(app)
    
    # Run everything
    asyncio.run(run_all())


if __name__ == '__main__':
    main()
