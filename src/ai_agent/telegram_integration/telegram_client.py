"""
Telegram Client Manager
Handles Telegram account creation, authentication, and client management
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from ..utils.logger import get_logger
from ..utils.exceptions import ValidationError


class TelegramClientManager:
    """Manages Telegram client connection and authentication"""
    
    def __init__(self, session_name: str = "vexis_telegram", config: Optional[Dict[str, Any]] = None):
        self.logger = get_logger("telegram_client")
        self.session_name = session_name
        self.config = config or {}
        
        # Check if bot_token is configured (Bot API mode) FIRST
        self.bot_token = self.config.get("bot_token", "")
        self.use_bot_api = bool(self.bot_token and self.bot_token.strip())

        # Set API credentials (only required for user account mode)
        # Bot mode can work with just bot_token
        self.api_id = self.config.get("api_id") or os.getenv("TELEGRAM_API_ID")
        self.api_hash = self.config.get("api_hash") or os.getenv("TELEGRAM_API_HASH")
        
        # Only validate API credentials for user account mode
        if not self.use_bot_api:
            if not self.api_id or not isinstance(self.api_id, int) or self.api_id <= 0:
                raise ValidationError("Invalid api_id: must be a positive integer (get from https://my.telegram.org)")
            if not self.api_hash or not isinstance(self.api_hash, str) or len(self.api_hash) < 8:
                raise ValidationError("Invalid api_hash: must be a non-empty string with at least 8 characters")

        if self.use_bot_api:
            # Bot API mode - use bot_token
            self.logger.info("Using Bot API mode with bot_token")
        
        # Session file path
        self.session_dir = Path.home() / ".vexis" / "telegram_sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_path = self.session_dir / f"{session_name}.session"
        
        self.client: Optional[TelegramClient] = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to Telegram"""
        try:
            if self.use_bot_api:
                # Bot API mode - use bot_token only (no api_id/api_hash needed)
                self.client = TelegramClient(
                    str(self.session_path),
                    self.api_id or 0,  # Default to 0 for bot mode
                    self.api_hash or ""  # Default to empty string for bot mode
                )
            else:
                # User Account API mode - requires api_id/api_hash
                self.client = TelegramClient(
                    str(self.session_path),
                    self.api_id,
                    self.api_hash
                )

            await self.client.connect()

            # For bot mode, sign in with bot token
            if self.use_bot_api:
                await self.client.sign_in(bot_token=self.bot_token)

            self.is_connected = True
            self.logger.info("Telegram client connected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Telegram: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
            self.logger.info("Telegram client disconnected")
    
    async def is_authorized(self) -> bool:
        """Check if the client is authorized"""
        if not self.client or not self.is_connected:
            return False
        try:
            return await self.client.is_authorized()
        except AttributeError:
            # Fallback for older Telethon versions
            return await self.client.is_user_authorized()
    
    async def create_account_interactive(self, phone_number: str) -> bool:
        """
        Create a new Telegram account interactively via CLI
        
        Args:
            phone_number: Phone number with country code (e.g., +1234567890)
            
        Returns:
            True if account creation successful, False otherwise
        """
        try:
            if not self.client or not self.is_connected:
                await self.connect()
            
            # Check if already authorized
            if await self.is_authorized():
                self.logger.info("Already authorized with existing account")
                return True
            
            # Send code request
            self.logger.info(f"Sending code request to {phone_number}")
            await self.client.send_code_request(phone_number)
            
            # Prompt for verification code
            print("\n" + "="*60)
            print("TELEGRAM ACCOUNT VERIFICATION")
            print("="*60)
            print(f"A verification code has been sent to {phone_number}")
            print("Please enter the code below:")
            
            code = input("Verification code: ").strip()
            
            # Sign in with phone and code
            await self.client.sign_in(phone_number, code)
            
            # Check if 2FA password is needed
            try:
                await self.client.get_me()
                self.logger.info("Account created and authorized successfully")
                print("\n✓ Telegram account created and authorized successfully!")
                return True
                
            except SessionPasswordNeededError:
                print("\nTwo-factor authentication is enabled.")
                password = input("Please enter your 2FA password: ").strip()
                await self.client.sign_in(password=password)
                self.logger.info("Account created with 2FA successfully")
                print("\n✓ Telegram account created with 2FA successfully!")
                return True
                
        except PhoneCodeInvalidError:
            self.logger.error("Invalid verification code")
            print("\n✗ Invalid verification code. Please try again.")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create account: {e}")
            print(f"\n✗ Failed to create account: {e}")
            return False
    
    async def use_existing_account(self) -> bool:
        """
        Use an existing Telegram account from session
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client or not self.is_connected:
                await self.connect()
            
            if not self.client:
                self.logger.error("Failed to initialize Telegram client")
                print("\n✗ Failed to initialize Telegram client")
                return False
            
            if await self.is_authorized():
                me = await self.client.get_me()
                if me:
                    username_display = f"@{me.username}" if me.username else "no username"
                    self.logger.info(f"Authorized as: {me.first_name} ({username_display})")
                    print(f"\n✓ Connected to Telegram as: {me.first_name} ({username_display})")
                else:
                    self.logger.info("Authorized successfully")
                    print("\n✓ Connected to Telegram successfully")
                return True
            else:
                self.logger.warning("No existing session found. Please create an account first.")
                print("\n✗ No existing session found. Please create an account first using --telegram-setup")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to use existing account: {e}")
            print(f"\n✗ Failed to use existing account: {e}")
            return False
    
    async def get_me(self):
        """Get current user information"""
        if not self.client or not self.is_connected:
            await self.connect()
        
        return await self.client.get_me()
    
    async def send_message(self, recipient: str, message: str) -> bool:
        """
        Send a message to a recipient
        
        Args:
            recipient: Username, phone number, or user ID
            message: Message content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not recipient or not recipient.strip():
                self.logger.error("Recipient is required")
                return False
            
            if not message or not message.strip():
                self.logger.error("Message content is required")
                return False
            
            if not self.client or not self.is_connected:
                await self.connect()
            
            if not self.client:
                self.logger.error("Telegram client not initialized")
                return False
            
            # Resolve recipient with fallbacks (username, phone, or ID)
            raw_recipient = str(recipient).strip()
            candidates = []

            if raw_recipient:
                candidates.append(raw_recipient)

            # Username normalization
            if raw_recipient.startswith("@"):
                candidates.append(raw_recipient.lstrip("@"))
            elif raw_recipient.isalpha() or "_" in raw_recipient:
                candidates.append(f"@{raw_recipient}")

            # Numeric user id fallback
            if raw_recipient.isdigit():
                candidates.append(int(raw_recipient))

            # Phone normalization fallback
            if raw_recipient.startswith("+") and raw_recipient[1:].isdigit():
                candidates.append(raw_recipient[1:])

            # De-duplicate while preserving order
            unique_candidates = []
            for candidate in candidates:
                if candidate not in unique_candidates:
                    unique_candidates.append(candidate)

            entity = None
            resolve_error = None
            for candidate in unique_candidates:
                try:
                    entity = await self.client.get_entity(candidate)
                    if entity:
                        break
                except Exception as e:
                    resolve_error = e

            # Final fallback: search existing dialogs by username / phone / id
            if not entity:
                try:
                    target_plain = raw_recipient.lstrip("@").strip().lower()
                    async for dialog in self.client.iter_dialogs():
                        ent = dialog.entity
                        username = getattr(ent, "username", None)
                        phone = getattr(ent, "phone", None)
                        user_id = str(getattr(ent, "id", ""))
                        if (
                            (username and username.lower() == target_plain)
                            or (phone and (phone == raw_recipient or phone == raw_recipient.lstrip("+")))
                            or (raw_recipient.isdigit() and user_id == raw_recipient)
                        ):
                            entity = ent
                            break
                except Exception as e:
                    resolve_error = resolve_error or e

            if not entity:
                known_fix = (
                    "Could not resolve recipient. Known fixes: ensure user has started chat with the bot, "
                    "run `python3 run.py --telegram-setup`, and re-sync contacts with `--telegram-sync`."
                )
                if resolve_error:
                    self.logger.error(f"{known_fix} recipient={recipient} error={resolve_error}")
                else:
                    self.logger.error(f"{known_fix} recipient={recipient}")
                return False
            
            # Send message
            await self.client.send_message(entity, message)
            self.logger.info(f"Message sent to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {recipient}: {e}")
            return False
    
    async def get_dialogs(self) -> List[Any]:
        """Get all dialogs (chats)"""
        if not self.client or not self.is_connected:
            await self.connect()
        
        dialogs = []
        async for dialog in self.client.iter_dialogs():
            dialogs.append(dialog)
        
        return dialogs
    
    async def get_contacts(self) -> List[Any]:
        """Get all contacts"""
        if not self.client or not self.is_connected:
            await self.connect()
        
        # Use iter_dialogs to get contacts (get_contacts may not be available)
        contacts = []
        async for dialog in self.client.iter_dialogs():
            if dialog.is_user:
                contacts.append(dialog.entity)
        
        return contacts
    
    def register_message_handler(self, callback):
        """Register a callback for incoming messages"""
        if not self.client:
            raise ValidationError("Telegram client not initialized")
        
        @self.client.on(events.NewMessage)
        async def handler(event):
            await callback(event)
        
        self.logger.info("Message handler registered")


async def get_telegram_client(config: Optional[Dict[str, Any]] = None) -> TelegramClientManager:
    """Get or create Telegram client manager instance"""
    return TelegramClientManager(config=config)
