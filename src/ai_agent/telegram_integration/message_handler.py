"""
Message Handler
Handles incoming Telegram messages and integrates with Phase 1 input
"""

import asyncio
from typing import Callable, Optional, Dict, Any
from ..utils.logger import get_logger
from .telegram_client import TelegramClientManager


class MessageHandler:
    """Handles incoming Telegram messages for Phase 1 input"""
    
    def __init__(self, telegram_client: TelegramClientManager):
        self.logger = get_logger("message_handler")
        self.telegram_client = telegram_client
        self.message_queue = asyncio.Queue()
        self.prompt_callback: Optional[Callable] = None
        self.prompt_callback_with_sender: Optional[Callable] = None
        self.is_running = False
        
    def set_prompt_callback(self, callback: Callable[[str], None]):
        """
        Set callback function to handle incoming prompts
        
        Args:
            callback: Function that takes a prompt string and processes it
        """
        self.prompt_callback = callback
        self.prompt_callback_with_sender = None
        self.logger.info("Prompt callback registered")
    
    def set_prompt_callback_with_sender(self, callback: Callable[[str, Any], None]):
        """
        Set callback function to handle incoming prompts with sender info
        
        Args:
            callback: Function that takes prompt string and sender info
        """
        self.prompt_callback_with_sender = callback
        self.prompt_callback = None
        self.logger.info("Prompt callback with sender registered")
    
    async def start_listening(self, authorized_users: Optional[list] = None):
        """
        Start listening for incoming Telegram messages
        
        Args:
            authorized_users: List of authorized usernames/IDs (None means all users)
        """
        if self.is_running:
            self.logger.warning("Message handler already running")
            return
        
        self.is_running = True
        self.authorized_users = authorized_users or []
        
        # Register message handler
        self.telegram_client.register_message_handler(self._handle_message)
        
        self.logger.info(f"Started listening for messages (authorized: {len(self.authorized_users) if authorized_users else 'all'})")
        print(f"\n📱 Listening for Telegram messages...")
        if authorized_users:
            print(f"   Authorized users: {', '.join(authorized_users)}")
        
        # Keep the client running
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("Message handler stopped")
    
    def stop_listening(self):
        """Stop listening for incoming messages"""
        self.is_running = False
        self.logger.info("Stopped listening for messages")
    
    async def _handle_message(self, event):
        """
        Handle incoming Telegram message
        
        Args:
            event: Telethon NewMessage event
        """
        try:
            if not event or not event.message:
                return
            
            sender = await event.message.get_sender()
            if not sender:
                self.logger.warning("Received message with no sender")
                return
            
            sender_username = sender.username if sender else None
            sender_id = sender.id if sender else None
            sender_phone = sender.phone if sender else None
            
            # Check if sender is authorized
            if self.authorized_users:
                is_authorized = False
                for auth_user in self.authorized_users:
                    if (sender_username and auth_user.lstrip("@").lower() == sender_username.lower()) or \
                       (str(sender_id) == str(auth_user)) or \
                       (sender_phone and sender_phone == auth_user):
                        is_authorized = True
                        break
                
                if not is_authorized:
                    self.logger.warning(f"Unauthorized message from {sender_username or sender_id}")
                    return
            
            # Get message text
            message_text = event.message.message
            
            if not message_text or not message_text.strip():
                return
            
            self.logger.info(f"Received message from {sender_username or sender_id}: {message_text[:50]}...")
            
            # Add to queue
            await self.message_queue.put({
                "sender": sender_username or str(sender_id),
                "message": message_text,
                "timestamp": event.message.date
            })
            
            # Call prompt callback if registered
            if self.prompt_callback_with_sender:
                try:
                    # Execute callback directly in async context
                    self.prompt_callback_with_sender(message_text, sender)
                except Exception as e:
                    self.logger.error(f"Error in prompt callback: {e}")
            elif self.prompt_callback:
                try:
                    # Execute callback directly in async context
                    self.prompt_callback(message_text)
                except Exception as e:
                    self.logger.error(f"Error in prompt callback: {e}")
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def get_pending_messages(self) -> list:
        """Get all pending messages from queue"""
        messages = []
        while not self.message_queue.empty():
            messages.append(await self.message_queue.get())
        return messages
    
    async def has_pending_messages(self) -> bool:
        """Check if there are pending messages"""
        return not self.message_queue.empty()
