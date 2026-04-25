"""
Telegram Integration Module for VEXIS-CLI
Provides Telegram account management, contact synchronization, message handling, and error notifications
"""

from .message_handler import MessageHandler

try:
    from .telegram_client import TelegramClientManager
    from .contact_manager import ContactManager
    from .error_notifier import TelegramErrorNotifier, get_error_notifier, send_error_notification_sync
except ImportError:
    # Allow partial import in minimal/runtime-constrained environments
    TelegramClientManager = None
    ContactManager = None
    TelegramErrorNotifier = None
    get_error_notifier = None
    send_error_notification_sync = None

__all__ = [
    'TelegramClientManager',
    'ContactManager',
    'MessageHandler',
    'TelegramErrorNotifier',
    'get_error_notifier',
    'send_error_notification_sync'
]
