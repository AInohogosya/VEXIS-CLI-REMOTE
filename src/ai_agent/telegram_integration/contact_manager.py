"""
Contact Manager
Handles synchronization between config contacts and Telegram contacts
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from ..utils.logger import get_logger
from ..utils.config import load_config
from .telegram_client import TelegramClientManager


class ContactManager:
    """Manages contact synchronization between config and Telegram"""
    
    def __init__(self, telegram_client: TelegramClientManager, contacts: Optional[list] = None):
        self.logger = get_logger("contact_manager")
        self.telegram_client = telegram_client
        self.contacts = contacts or []
        
    def load_contacts_from_config(self) -> Dict[str, Any]:
        """
        Load contacts from config (passed directly to constructor)
        
        Returns:
            Dictionary with contacts configuration
        """
        return {"contacts": self.contacts}
    
    async def sync_contacts_to_telegram(self) -> bool:
        """
        Synchronize contacts from config to Telegram

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load contacts from config
            contacts_config = self.load_contacts_from_config()
            contacts = contacts_config.get("contacts", [])

            if not contacts:
                self.logger.warning("No contacts found in config")
                print("\n⚠ No contacts found in config file")
                return False

            self.logger.info(f"Found {len(contacts)} contacts in config")
            print(f"\nFound {len(contacts)} contacts in config:")

            # Display contacts
            for i, contact in enumerate(contacts, 1):
                name = contact.get("name", "Unknown")
                identifier = contact.get("telegram", contact.get("phone", contact.get("username", "Unknown")))
                print(f"  {i}. {name} ({identifier})")

            # Bot API mode: cannot access Telegram contact list. Trust config identifiers.
            if getattr(self.telegram_client, 'use_bot_http_api', False):
                self.logger.info("Bot API mode: skipping contact validation, using configured contacts directly")
                valid_contacts = []
                invalid_contacts = []

                for contact in contacts:
                    # Determine identifier: prefer telegram (username), then phone, then user_id
                    identifier = None
                    if contact.get("telegram"):
                        identifier = contact["telegram"].strip()
                    elif contact.get("phone"):
                        identifier = contact["phone"].strip()
                    elif contact.get("user_id"):
                        identifier = str(contact["user_id"]).strip()

                    if identifier:
                        valid_contacts.append({
                            "name": contact.get("name", "Unknown"),
                            "identifier": identifier,
                            "config": contact
                        })
                    else:
                        invalid_contacts.append({
                            "name": contact.get("name", "Unknown"),
                            "identifier": None
                        })

                print(f"\n✓ Bot API mode: accepting {len(valid_contacts)} contact(s) from config (no validation)")
                if invalid_contacts:
                    print(f"✗ Invalid contacts (missing identifier): {len(invalid_contacts)}")
                    for c in invalid_contacts:
                        print(f"  - {c['name']}")

                self.valid_contacts = valid_contacts
                self.invalid_contacts = invalid_contacts
                return len(valid_contacts) > 0

            # User account mode: validate against Telegram contacts
            if not self.telegram_client.client:
                self.logger.error("Telegram client not initialized")
                print("\n✗ Telegram client not initialized")
                return False

            telegram_contacts = await self.telegram_client.get_contacts()
            if not telegram_contacts:
                self.logger.warning("No contacts found in Telegram account")
                print("\n⚠ No contacts found in Telegram account")

            telegram_usernames = {c.username.lower() for c in telegram_contacts if c.username}
            telegram_phones = {c.phone for c in telegram_contacts if c.phone}

            valid_contacts = []
            invalid_contacts = []

            for contact in contacts:
                name = contact.get("name", "Unknown")
                telegram_username = contact.get("telegram", "").strip().lstrip("@")
                phone = contact.get("phone", "").strip()
                user_id = contact.get("user_id")

                # Check if contact exists in Telegram
                found = False
                identifier = None

                if telegram_username and telegram_username.lower() in telegram_usernames:
                    found = True
                    identifier = f"@{telegram_username}"
                elif phone and phone in telegram_phones:
                    found = True
                    identifier = phone
                elif user_id:
                    # Try to resolve by user ID
                    try:
                        entity = await self.telegram_client.client.get_entity(user_id)
                        if entity:
                            found = True
                            identifier = str(user_id)
                    except Exception as e:
                        self.logger.debug(f"Could not resolve user_id {user_id}: {e}")

                if found:
                    valid_contacts.append({
                        "name": name,
                        "identifier": identifier,
                        "config": contact
                    })
                else:
                    invalid_contacts.append({
                        "name": name,
                        "identifier": telegram_username or phone or str(user_id),
                        "config": contact
                    })

            # Report results
            print(f"\n✓ Valid contacts (found in Telegram): {len(valid_contacts)}")
            if invalid_contacts:
                print(f"✗ Invalid contacts (not found in Telegram): {len(invalid_contacts)}")
                for contact in invalid_contacts:
                    print(f"  - {contact['name']} ({contact['identifier']})")

            # Save validated contacts
            self.valid_contacts = valid_contacts
            self.invalid_contacts = invalid_contacts

            return len(valid_contacts) > 0

        except Exception as e:
            self.logger.error(f"Failed to sync contacts: {e}")
            print(f"\n✗ Failed to sync contacts: {e}")
            return False
    
    def get_valid_contacts(self) -> List[Dict[str, Any]]:
        """Get list of validated contacts"""
        return getattr(self, "valid_contacts", [])
    
    def get_contact_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a contact by name
        
        Args:
            name: Contact name
            
        Returns:
            Contact dictionary or None if not found
        """
        if not name or not name.strip():
            self.logger.warning("Contact name is required")
            return None
        
        for contact in self.get_valid_contacts():
            if contact.get("name") and contact["name"].lower() == name.lower():
                return contact
        return None
    
    def get_all_contact_identifiers(self) -> List[str]:
        """Get all valid contact identifiers (usernames, phones, IDs)"""
        return [c["identifier"] for c in self.get_valid_contacts()]
