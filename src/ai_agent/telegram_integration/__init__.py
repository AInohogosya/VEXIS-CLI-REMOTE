"""
Telegram Integration Module for VEXIS-CLI
Provides Telegram account management, contact synchronization, message handling, and error notifications
"""

from .telegram_client import TelegramClientManager
from .contact_manager import ContactManager
from .message_handler import MessageHandler
from .error_notifier import TelegramErrorNotifier, get_error_notifier, send_error_notification_sync

__all__ = [
    'TelegramClientManager',
    'ContactManager',
    'MessageHandler',
    'TelegramErrorNotifier',
    'get_error_notifier',
    'send_error_notification_sync'
]
