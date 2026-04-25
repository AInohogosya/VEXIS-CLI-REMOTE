"""
Message Handler
Handles incoming Telegram messages and integrates with Phase 1 input
"""

import asyncio
from typing import Callable, Optional, Dict, Any
from ..utils.logger import get_logger
from .telegram_client import TelegramClientManager
from ..core_processing.terminal_history import get_terminal_history


class MessageHandler:
    """Handles incoming Telegram messages for Phase 1 input"""
    
    def __init__(self, telegram_client: TelegramClientManager):
        self.logger = get_logger("message_handler")
        self.telegram_client = telegram_client
        self.message_queue = asyncio.Queue()
        self.prompt_callback: Optional[Callable] = None
        self.prompt_callback_with_sender: Optional[Callable] = None
        self.setup_callback_with_sender: Optional[Callable] = None
        self.is_running = False
        self.is_processing = False
        self.current_task: Optional[asyncio.Task] = None
        self.task_queue: list = []
        self.max_queue_size = 15
        
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

    def set_setup_callback_with_sender(self, callback: Callable[[str, Any], None]):
        """
        Set callback function to handle /setup self-healing command with sender info

        Args:
            callback: Function that takes setup command text and sender info
        """
        self.setup_callback_with_sender = callback
        self.logger.info("Setup callback with sender registered")
    
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
        Handle incoming Telegram message with enhanced error recovery
        
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
            self.logger.info(f"Message received - username: {sender_username}, id: {sender_id}, phone: {sender_phone}")
            self.logger.info(f"Authorized users config: {self.authorized_users}")
            
            if self.authorized_users:
                is_authorized = False
                for auth_user in self.authorized_users:
                    self.logger.debug(f"Checking against auth_user: '{auth_user}'")
                    username_match = sender_username and auth_user.lstrip("@").lower() == sender_username.lower()
                    id_match = str(sender_id) == str(auth_user)
                    phone_match = sender_phone and sender_phone == auth_user
                    
                    self.logger.debug(f"Match results - username: {username_match}, id: {id_match}, phone: {phone_match}")
                    
                    if username_match or id_match or phone_match:
                        is_authorized = True
                        break
                
                if not is_authorized:
                    self.logger.warning(f"Unauthorized message from {sender_username or sender_id}")
                    try:
                        await event.reply(
                            "❌ You are not authorized to use this listener.\n"
                            "Known fix: add your username/id to telegram.authorized_users in config.yaml,\n"
                            "then run `python3 run.py --telegram-setup` and restart `--telegram-listen`."
                        )
                    except Exception as reply_error:
                        self.logger.debug(f"Failed to send unauthorized notice: {reply_error}")
                    return
            
            # Get message text
            message_text = event.message.message
            
            if not message_text or not message_text.strip():
                return
            
            self.logger.info(f"Received message from {sender_username or sender_id}: {message_text[:50]}...")

            # Explicit self-healing setup command
            normalized_text = message_text.strip().lower()
            if normalized_text.startswith("/setup"):
                self.logger.info("Detected /setup command - running Telegram self-healing flow")
                try:
                    await event.reply("🛠 Running Telegram setup checks and auto-fix flow...")
                except Exception:
                    pass

                if self.setup_callback_with_sender:
                    try:
                        if asyncio.iscoroutinefunction(self.setup_callback_with_sender):
                            await self.setup_callback_with_sender(message_text, sender)
                        else:
                            self.setup_callback_with_sender(message_text, sender)
                    except Exception as setup_error:
                        self.logger.error(f"Error in /setup callback: {setup_error}")
                        try:
                            await event.reply(
                                "❌ Setup self-healing failed.\n"
                                "Please run `python3 run.py --telegram-setup` on the host and retry."
                            )
                        except Exception:
                            pass
                else:
                    try:
                        await event.reply(
                            "ℹ️ Setup callback is not configured in this runtime.\n"
                            "Run `python3 run.py --telegram-setup` and then `python3 run.py --telegram-listen`."
                        )
                    except Exception:
                        pass
                return
            
            # Check for /remote command to reset conversation history
            if "/remote" in message_text:
                self.logger.info(f"Detected /remote command, resetting conversation history")
                try:
                    terminal_history = get_terminal_history()
                    terminal_history.clear_history()
                    self.logger.info("Conversation history successfully reset")
                except Exception as e:
                    self.logger.error(f"Failed to reset conversation history: {e}")
            
            # Add to message queue
            await self.message_queue.put({
                "sender": sender_username or str(sender_id),
                "message": message_text,
                "timestamp": event.message.date
            })
            
            # Handle task queuing
            task_data = {
                "sender": sender,
                "message": message_text,
                "sender_username": sender_username,
                "sender_id": sender_id
            }
            
            if self.is_processing:
                # A task is currently running
                if len(self.task_queue) >= self.max_queue_size:
                    self.logger.warning(f"Task queue is full (max {self.max_queue_size}). Dropping new task.")
                    return
                # Add new task to queue
                self.task_queue.append(task_data)
                self.logger.info(f"Task added to queue. Queue size: {len(self.task_queue)}/{self.max_queue_size}")
                # Terminate current task
                await self.terminate_current_task()
                # Process queue (will execute the new task)
                await self._process_queue()
            else:
                # No task running, execute immediately
                await self._execute_task(task_data)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            # Don't re-raise - allow the listener to continue processing other messages
            self.logger.info("Listener recovered from message handling error")
    
    async def _execute_task(self, task_data: Dict[str, Any]):
        """
        Execute a single task with comprehensive error recovery
        
        Args:
            task_data: Dictionary containing task information
        """
        self.is_processing = True
        message_text = task_data["message"]
        sender = task_data["sender"]
        
        try:
            # Call prompt callback if registered
            if self.prompt_callback_with_sender:
                try:
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(self.prompt_callback_with_sender):
                        # Create and track the task
                        self.current_task = asyncio.create_task(self.prompt_callback_with_sender(message_text, sender))
                        await self.current_task
                    else:
                        # Execute synchronous callback
                        self.prompt_callback_with_sender(message_text, sender)
                except asyncio.CancelledError:
                    self.logger.info("Task execution was cancelled")
                    raise
                except Exception as e:
                    self.logger.error(f"Error in prompt callback: {e}")
                    # Don't re-raise - allow the listener to continue
                    self.logger.info("Listener will continue running despite error")
            elif self.prompt_callback:
                try:
                    # Check if callback is async
                    if asyncio.iscoroutinefunction(self.prompt_callback):
                        # Create and track the task
                        self.current_task = asyncio.create_task(self.prompt_callback(message_text))
                        await self.current_task
                    else:
                        # Execute synchronous callback
                        self.prompt_callback(message_text)
                except asyncio.CancelledError:
                    self.logger.info("Task execution was cancelled")
                    raise
                except Exception as e:
                    self.logger.error(f"Error in prompt callback: {e}")
                    # Don't re-raise - allow the listener to continue
                    self.logger.info("Listener will continue running despite error")
        except Exception as e:
            # Catch any unexpected errors at the task level
            self.logger.error(f"Unexpected error during task execution: {e}")
            # Ensure the listener continues running
            self.logger.info("Listener recovered from unexpected error")
        finally:
            self.current_task = None
            self.is_processing = False
            # Process next task in queue if any
            await self._process_queue()
    
    async def _process_queue(self):
        """Process the next task in the queue"""
        if self.task_queue and not self.is_processing:
            next_task = self.task_queue.pop(0)
            self.logger.info(f"Processing next task from queue. Remaining: {len(self.task_queue)}")
            await self._execute_task(next_task)
    
    async def terminate_current_task(self):
        """Terminate the currently running task"""
        if self.current_task and not self.current_task.done():
            self.logger.info("Terminating current task...")
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                self.logger.info("Current task cancelled successfully")
            self.current_task = None
            self.is_processing = False
    
    def get_queue_size(self) -> int:
        """Get the current size of the task queue"""
        return len(self.task_queue)
    
    async def get_pending_messages(self) -> list:
        """Get all pending messages from queue"""
        messages = []
        while not self.message_queue.empty():
            messages.append(await self.message_queue.get())
        return messages
    
    async def has_pending_messages(self) -> bool:
        """Check if there are pending messages"""
        return not self.message_queue.empty()
