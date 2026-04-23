"""
Telegram Error Notifier
Centralized utility for sending error notifications via Telegram
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from .telegram_client import get_telegram_client
from ..utils.logger import get_logger
from ..utils.config import load_config


class TelegramErrorNotifier:
    """Centralized error notification system via Telegram"""
    
    def __init__(self):
        self.logger = get_logger("telegram_error_notifier")
        self._client = None
        self._enabled = False
        self._contact_manager = None
    
    async def _initialize(self):
        """Initialize Telegram client for error notifications"""
        if self._enabled:
            return True
        
        try:
            config = load_config()
            
            if not config.telegram.enabled:
                self.logger.info("Telegram integration is not enabled")
                return False
            
            telegram_config = {
                "api_id": config.telegram.api_id,
                "api_hash": config.telegram.api_hash,
                "session_name": config.telegram.session_name,
                "bot_token": getattr(config.telegram, "bot_token", ""),
                "bot_username": getattr(config.telegram, "bot_username", "")
            }
            
            from .contact_manager import ContactManager
            
            self._client = await get_telegram_client(config=telegram_config)
            
            if await self._client.connect():
                if await self._client.is_authorized():
                    self._contact_manager = ContactManager(self._client, config.telegram.contacts)
                    self._enabled = True
                    self.logger.info("Telegram error notifier initialized")
                    return True
                else:
                    await self._client.disconnect()
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram error notifier: {e}")
            return False
    
    async def send_error_notification(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        recipient: Optional[str] = None
    ) -> bool:
        """
        Send error notification via Telegram
        
        Args:
            error_message: The error message to send
            context: Additional context information (dict)
            recipient: Specific recipient (username/phone/id). If None, sends to all configured recipients
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not await self._initialize():
            return False
        
        try:
            # Format error message
            formatted_message = self._format_error_message(error_message, context)
            
            # Determine recipients
            recipients = []
            if recipient:
                recipients = [recipient]
            else:
                # Send to all configured output recipients
                config = load_config()
                recipients = config.telegram.output_recipients or []
            
            if not recipients:
                self.logger.warning("No recipients configured for error notifications")
                return False
            
            # Send to each recipient
            success_count = 0
            for recipient_name in recipients:
                try:
                    contact = self._contact_manager.get_contact_by_name(recipient_name)
                    if contact:
                        await self._client.send_message(contact["identifier"], formatted_message)
                        success_count += 1
                        self.logger.info(f"Error notification sent to {recipient_name}")
                except Exception as e:
                    self.logger.error(f"Failed to send error notification to {recipient_name}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")
            return False
    
    def _format_error_message(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format error message for Telegram"""
        msg = f"❌ **VEXIS-CLI Error Notification**\n\n"
        msg += f"{error_message}\n\n"
        
        if context:
            msg += f"**Context:**\n"
            for key, value in context.items():
                if isinstance(value, str):
                    msg += f"• {key}: {value[:200]}\n"
                else:
                    msg += f"• {key}: {str(value)[:200]}\n"
            msg += "\n"
        
        msg += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        msg += f"\nThe system has recovered and is ready for new commands."
        
        return msg
    
    async def cleanup(self):
        """Cleanup Telegram resources"""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")


# Singleton instance
_notifier_instance: Optional[TelegramErrorNotifier] = None


def get_error_notifier() -> TelegramErrorNotifier:
    """Get the singleton error notifier instance"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = TelegramErrorNotifier()
    return _notifier_instance


async def send_error_notification_sync(
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
    recipient: Optional[str] = None
) -> bool:
    """
    Synchronous wrapper for sending error notifications
    
    Args:
        error_message: The error message to send
        context: Additional context information (dict)
        recipient: Specific recipient (username/phone/id)
        
    Returns:
        True if sent successfully, False otherwise
    """
    notifier = get_error_notifier()
    
    # Run async function in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a task
            asyncio.create_task(notifier.send_error_notification(error_message, context, recipient))
            return True
        else:
            # If loop is not running, run it
            return loop.run_until_complete(notifier.send_error_notification(error_message, context, recipient))
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(notifier.send_error_notification(error_message, context, recipient))
