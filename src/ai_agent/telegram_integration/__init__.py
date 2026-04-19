"""
Telegram Integration Module for VEXIS-CLI
Provides Telegram account management, contact synchronization, and message handling
"""

from .telegram_client import TelegramClientManager
from .contact_manager import ContactManager
from .message_handler import MessageHandler

__all__ = ['TelegramClientManager', 'ContactManager', 'MessageHandler']
