"""
5-Phase Pipeline Execution Engine for CLI AI Agent System

Phase 1: Command Suggestion (User Prompt → Base Model)
Phase 2: Command Extraction (Phase 1 Output → Single Code Block)
Phase 3: Command Execution (Terminal Injection)
Phase 4: Log Evaluation and Re-execution Decision
Phase 5: Summary Generation and Display
"""

import re
import time
import platform
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..external_integration.model_runner import ModelRunner, TaskType, ModelRequest, ModelResponse
from ..utils.exceptions import ExecutionError, ValidationError
from ..utils.logger import get_logger
from .terminal_history import TerminalHistory, get_terminal_history, TerminalEntryType


class PipelinePhase(Enum):
    """5-Phase Pipeline phases"""
    PHASE1_COMMAND_SUGGESTION = "phase1_command_suggestion"
    PHASE2_COMMAND_EXTRACTION = "phase2_command_extraction"
    PHASE3_COMMAND_EXECUTION = "phase3_command_execution"
    PHASE4_LOG_EVALUATION = "phase4_log_evaluation"
    PHASE5_SUMMARY_GENERATION = "phase5_summary_generation"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineContext:
    """Context for tracking 5-phase pipeline execution"""
    user_prompt: str
    phase1_output: Optional[str] = None
    extracted_commands: Optional[str] = None
    terminal_log: str = ""
    phase4_output: Optional[str] = None
    final_summary: Optional[str] = None
    current_phase: PipelinePhase = PipelinePhase.PHASE1_COMMAND_SUGGESTION
    iteration_count: int = 0
    max_iterations: int = 10
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    phase2_consecutive_failures: int = 0
    phase2_goal_summary: Optional[str] = None


class FivePhaseEngine:
    """
    5-Phase Pipeline Execution Engine
    
    Implements the complete 5-phase architecture:
    - Phase 1: Command Suggestion
    - Phase 2: Command Extraction
    - Phase 3: Command Execution
    - Phase 4: Log Evaluation
    - Phase 5: Summary Generation
    """
    
    def __init__(self, provider: str = None, model: str = None, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger("five_phase_engine")
        
        # Initialize terminal history system
        self.terminal_history = get_terminal_history()
        
        # Initialize model runner with runtime provider and model
        self.model_runner = ModelRunner(provider=provider, model=model, config=self.config)
        
        # Configuration
        self.max_iterations = self.config.get("max_iterations", 300)
        self.command_timeout = self.config.get("command_timeout", 30)
        self.task_timeout = self.config.get("task_timeout", 300)
        
        # Telegram integration (lazy initialization)
        self._telegram_client = None
        self._telegram_contact_manager = None
        self._telegram_enabled = False
        
        self.logger.info("5-Phase Pipeline Engine initialized")
    
    def _init_telegram(self):
        """Initialize Telegram integration if enabled"""
        if self._telegram_enabled:
            return  # Already initialized
        
        try:
            from ..utils.config import load_config
            config = load_config()
            
            if not config.telegram.enabled:
                return
            
            import asyncio
            from ..telegram_integration.telegram_client import get_telegram_client
            from ..telegram_integration.contact_manager import ContactManager
            
            # Create Telegram client
            telegram_config = {
                "api_id": config.telegram.api_id,
                "api_hash": config.telegram.api_hash,
                "session_name": config.telegram.session_name
            }
            
            # Run async initialization
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def do_init():
                client = await get_telegram_client(config=telegram_config)
                if await client.connect():
                    if await client.is_authorized():
                        contact_manager = ContactManager(client, config.telegram.contacts)
                        await contact_manager.sync_contacts_to_telegram()
                        return client, contact_manager
                    else:
                        await client.disconnect()
                return None, None
            
            self._telegram_client, self._telegram_contact_manager = loop.run_until_complete(do_init())
            
            # Keep the event loop for later use
            self._telegram_loop = loop
            
            if self._telegram_client:
                self._telegram_enabled = True
                self.logger.info("Telegram integration initialized")
            else:
                loop.close()
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize Telegram integration: {e}")
            self._telegram_enabled = False
            if hasattr(self, '_telegram_loop') and self._telegram_loop:
                try:
                    self._telegram_loop.close()
                except:
                    pass
    
    def _cleanup_telegram(self):
        """Cleanup Telegram resources"""
        if self._telegram_client and self._telegram_loop:
            try:
                async def do_cleanup():
                    await self._telegram_client.disconnect()
                self._telegram_loop.run_until_complete(do_cleanup())
                self._telegram_loop.close()
            except Exception as e:
                self.logger.warning(f"Error during Telegram cleanup: {e}")
    
    def _send_via_telegram(self, message: str):
        """Send message via Telegram to configured recipients (synchronous wrapper)"""
        if not self._telegram_enabled or not self._telegram_client:
            return
        
        try:
            from ..utils.config import load_config
            config = load_config()
            
            recipients = config.telegram.output_recipients
            if not recipients:
                return
            
            async def do_send():
                for recipient_name in recipients:
                    contact = self._telegram_contact_manager.get_contact_by_name(recipient_name)
                    if contact:
                        await self._telegram_client.send_message(contact["identifier"], message)
                        self.logger.info(f"Sent Phase 5 output to {recipient_name} via Telegram")
            
            self._telegram_loop.run_until_complete(do_send())
            
        except Exception as e:
            self.logger.error(f"Failed to send via Telegram: {e}")
    
    def _check_timeout(self, context: PipelineContext) -> bool:
        """
        Check if the task has exceeded the timeout limit
        
        Args:
            context: Current pipeline context
            
        Returns:
            True if timeout has been exceeded, False otherwise
        """
        elapsed = time.time() - context.start_time
        if elapsed >= self.task_timeout:
            self.logger.warning(f"Task timeout exceeded: {elapsed:.2f}s / {self.task_timeout}s")
            return True
        return False
    
    def _save_timeout_conversation(self, context: PipelineContext):
        """
        Save conversation in Telegram-like format when timeout occurs
        
        Args:
            context: Current pipeline context
        """
        try:
            from datetime import datetime
            from pathlib import Path
            
            # Create conversation directory if it doesn't exist
            conv_dir = Path("terminal_history")
            conv_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            conv_file = conv_dir / f"timeout_conversation_{timestamp}.txt"
            
            elapsed = time.time() - context.start_time
            
            # Build Telegram-like conversation format
            conversation = []
            conversation.append("=" * 60)
            conversation.append(f"🚫 TASK TIMEOUT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            conversation.append("=" * 60)
            conversation.append(f"⏱️  Time elapsed: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
            conversation.append(f"⏱️  Time limit: {self.task_timeout} seconds ({self.task_timeout/60:.2f} minutes)")
            conversation.append("")
            conversation.append("-" * 60)
            conversation.append("📝 USER INSTRUCTION")
            conversation.append("-" * 60)
            conversation.append(context.user_prompt)
            conversation.append("")
            conversation.append("-" * 60)
            conversation.append("🤖 AI RESPONSE HISTORY")
            conversation.append("-" * 60)
            
            # Add phase outputs if available
            if context.phase1_output:
                conversation.append("")
                conversation.append("📍 Phase 1 - Command Suggestion:")
                conversation.append(context.phase1_output)
            
            if context.extracted_commands:
                conversation.append("")
                conversation.append("📍 Phase 2 - Extracted Commands:")
                conversation.append(context.extracted_commands)
            
            if context.terminal_log:
                conversation.append("")
                conversation.append("📍 Phase 3 - Terminal Output:")
                conversation.append(context.terminal_log)
            
            if context.phase4_output:
                conversation.append("")
                conversation.append("📍 Phase 4 - Log Evaluation:")
                conversation.append(context.phase4_output)
            
            conversation.append("")
            conversation.append("-" * 60)
            conversation.append(f"📊 STATUS: {context.current_phase.value}")
            conversation.append(f"🔄 Iterations: {context.iteration_count}")
            conversation.append("-" * 60)
            conversation.append("")
            conversation.append("💬 This conversation was saved due to task timeout.")
            conversation.append("💬 The task was stopped abruptly at the 45-minute limit.")
            conversation.append("=" * 60)
            
            # Write to file
            with open(conv_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(conversation))
            
            self.logger.info(f"Timeout conversation saved to: {conv_file}")
            print(f"\n🚫 Task timeout exceeded ({elapsed/60:.2f} minutes)")
            print(f"💬 Conversation saved to: {conv_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save timeout conversation: {e}")
    
    def execute_instruction(self, user_prompt: str) -> PipelineContext:
        """
        Execute user instruction through the 5-phase pipeline
        
        Args:
            user_prompt: Natural language instruction from user
            
        Returns:
            PipelineContext with complete execution results
        """
        self.logger.info("Starting 5-Phase Pipeline execution", user_prompt=user_prompt)
        
        # Clear terminal history to prevent showing completed tasks from previous sessions
        self.terminal_history.clear_history()
        
        # Initialize context
        context = PipelineContext(
            user_prompt=user_prompt,
            max_iterations=self.max_iterations,
            metadata={"os_info": self._get_os_info()}
        )
        
        try:
            # Check timeout before Phase 1
            if self._check_timeout(context):
                self._save_timeout_conversation(context)
                context.current_phase = PipelinePhase.FAILED
                context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                context.end_time = time.time()
                self._cleanup_telegram()
                return context
            
            # Phase 1: Command Suggestion
            if not self._run_phase1(context):
                context.current_phase = PipelinePhase.FAILED
                context.error = "Phase 1 (Command Suggestion) failed"
                return context
            
            # Check timeout after Phase 1
            if self._check_timeout(context):
                self._save_timeout_conversation(context)
                context.current_phase = PipelinePhase.FAILED
                context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                context.end_time = time.time()
                self._cleanup_telegram()
                return context
            
            # Phase 2-4 Loop: Extract, Execute, Evaluate until complete
            while context.iteration_count < context.max_iterations:
                # Check timeout before each iteration
                if self._check_timeout(context):
                    self._save_timeout_conversation(context)
                    context.current_phase = PipelinePhase.FAILED
                    context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                    context.end_time = time.time()
                    self._cleanup_telegram()
                    return context
                
                context.iteration_count += 1
                self.logger.info(f"Starting iteration {context.iteration_count}", 
                               phase=context.current_phase.value)
                
                # Phase 2: Command Extraction
                if not self._run_phase2(context):
                    # Check if we've had 3 consecutive Phase 2 failures
                    if context.phase2_consecutive_failures >= 3:
                        self.logger.warning("Phase 2 failed 3 times consecutively, forcing Phase 5")
                        # Break out of the loop to proceed to Phase 5
                        break
                    context.current_phase = PipelinePhase.FAILED
                    context.error = "Phase 2 (Command Extraction) failed"
                    return context
                
                # Check timeout after Phase 2
                if self._check_timeout(context):
                    self._save_timeout_conversation(context)
                    context.current_phase = PipelinePhase.FAILED
                    context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                    context.end_time = time.time()
                    self._cleanup_telegram()
                    return context
                
                # Phase 3: Command Execution
                if not self._run_phase3(context):
                    context.current_phase = PipelinePhase.FAILED
                    context.error = "Phase 3 (Command Execution) failed"
                    return context
                
                # Check timeout after Phase 3
                if self._check_timeout(context):
                    self._save_timeout_conversation(context)
                    context.current_phase = PipelinePhase.FAILED
                    context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                    context.end_time = time.time()
                    self._cleanup_telegram()
                    return context
                
                # Phase 4: Log Evaluation
                should_continue = self._run_phase4(context)
                
                # Check timeout after Phase 4
                if self._check_timeout(context):
                    self._save_timeout_conversation(context)
                    context.current_phase = PipelinePhase.FAILED
                    context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                    context.end_time = time.time()
                    self._cleanup_telegram()
                    return context
                
                if not should_continue:
                    # No "failure" in Phase 4 output - task is successful
                    break
                
                # Continue to next iteration (Phase 2-4 loop)
                self.logger.info(f"Phase 4 detected failure indicator, continuing to iteration {context.iteration_count + 1}")
            
            if context.iteration_count >= context.max_iterations:
                self.logger.warning("Maximum iterations reached, forcing completion")
            
            # Check timeout before Phase 5
            if self._check_timeout(context):
                self._save_timeout_conversation(context)
                context.current_phase = PipelinePhase.FAILED
                context.error = f"Task timeout exceeded after {time.time() - context.start_time:.2f} seconds"
                context.end_time = time.time()
                self._cleanup_telegram()
                return context
            
            # Phase 5: Summary Generation
            if not self._run_phase5(context):
                context.current_phase = PipelinePhase.FAILED
                context.error = "Phase 5 (Summary Generation) failed"
                return context
            
            context.current_phase = PipelinePhase.COMPLETED
            context.end_time = time.time()
            
            self.logger.info("5-Phase Pipeline execution completed successfully",
                           duration=context.end_time - context.start_time,
                           iterations=context.iteration_count)
            
            # Cleanup Telegram resources
            self._cleanup_telegram()
            
            return context
            
        except Exception as e:
            self.logger.error(f"5-Phase Pipeline execution failed: {e}")
            context.current_phase = PipelinePhase.FAILED
            context.error = str(e)
            context.end_time = time.time()
            # Cleanup Telegram resources on error
            self._cleanup_telegram()
            return context
    
    def _run_phase1(self, context: PipelineContext) -> bool:
        """
        Phase 1: Command Suggestion
        
        Send user prompt to base model with system prompt to get natural-language
        description of what commands should be run.
        
        If model execution fails, re-run Phase 1 (up to 3 retries).
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Phase 1: Command Suggestion started")
        context.current_phase = PipelinePhase.PHASE1_COMMAND_SUGGESTION
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                os_info = context.metadata.get("os_info", self._get_os_info())
                
                # Create request for Phase 1
                request = ModelRequest(
                    task_type=TaskType.PHASE1_COMMAND_SUGGESTION,
                    prompt=context.user_prompt,
                    context={
                        "user_prompt": context.user_prompt,
                        "os_info": os_info,
                    },
                    max_tokens=4000,
                    temperature=0.7
                )
                
                # Run model
                response = self.model_runner.run_model(request)
                
                if not response.success:
                    self.logger.error(f"Phase 1 model execution failed: {response.error}")
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Phase 1: Retrying (attempt {attempt + 2}/{max_retries})")
                        continue
                    return False
                
                context.phase1_output = response.content
                self.logger.info("Phase 1 completed successfully", 
                               output_length=len(response.content) if response.content else 0)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Phase 1 failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    self.logger.warning(f"Phase 1: Retrying (attempt {attempt + 2}/{max_retries})")
                    continue
                return False
        
        return False
    
    def _run_phase2(self, context: PipelineContext) -> bool:
        """
        Phase 2: Command Extraction
        
        Send Phase 1 output to base model to compress all necessary commands
        into a single code block.
        
        If no code block found, re-run Phase 2 (up to 3 retries).
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Phase 2: Command Extraction started")
        context.current_phase = PipelinePhase.PHASE2_COMMAND_EXTRACTION
        
        # Determine what to use as input for Phase 2
        # On first iteration, use Phase 1 output
        # On subsequent iterations, use Phase 4 output
        phase_input = context.phase4_output if context.phase4_output else context.phase1_output

        # First part of Phase 2: summarize the original plan objective in one sentence
        if not context.phase4_output and not context.phase2_goal_summary and phase_input:
            context.phase2_goal_summary = self._summarize_phase2_goal(phase_input)
            if context.phase2_goal_summary:
                context.metadata["phase2_goal_summary"] = context.phase2_goal_summary
                runtime_mode = self.config.get("runtime_mode", "terminal")
                if runtime_mode != "telegram":
                    print(f"\n🎯 Phase 2 goal summary: {context.phase2_goal_summary}\n")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create request for Phase 2
                request = ModelRequest(
                    task_type=TaskType.PHASE2_COMMAND_EXTRACTION,
                    prompt=phase_input,
                    context={
                        "phase_1_output": phase_input,
                    },
                    max_tokens=3000,
                    temperature=0.3
                )
                
                # Run model
                response = self.model_runner.run_model(request)
                
                if not response.success:
                    self.logger.error(f"Phase 2 model execution failed: {response.error}")
                    if attempt < max_retries - 1:
                        continue
                    context.phase2_consecutive_failures += 1
                    self._record_phase2_update(
                        context=context,
                        status="failed",
                        detail=(
                            f"Phase 2 model call failed (iteration {context.iteration_count}, "
                            f"attempt {attempt + 1}): {response.error}"
                        )
                    )
                    self.logger.warning(f"Phase 2 consecutive failures: {context.phase2_consecutive_failures}")
                    return False
                
                # Extract code block from response
                commands = self._extract_code_block(response.content)
                
                if commands:
                    context.extracted_commands = commands
                    # Reset consecutive failures counter on success
                    context.phase2_consecutive_failures = 0
                    self._record_phase2_update(
                        context=context,
                        status="success",
                        detail=f"Phase 2 completed (iteration {context.iteration_count}): extracted command block."
                    )
                    self.logger.info("Phase 2 completed successfully",
                                   commands_length=len(commands))

                    # Send Phase 2 completion update via Telegram if enabled
                    try:
                        from ..utils.config import load_config
                        cfg = load_config()
                        if cfg.telegram.send_phase2_end_updates:
                            # Build message content
                            message_parts = ["🎯 Phase 2 Completed\n"]
                            if context.phase2_goal_summary:
                                message_parts.append(f"Goal: {context.phase2_goal_summary}\n")
                            message_parts.append(f"\nExtracted commands:\n```\n{commands}\n```")
                            telegram_message = "".join(message_parts)
                            self._send_via_telegram(telegram_message)
                    except Exception as e:
                        self.logger.warning(f"Failed to send Phase 2 Telegram update: {e}")

                    return True
                else:
                    self.logger.warning(f"Phase 2: No code block found in attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    context.phase2_consecutive_failures += 1
                    self._record_phase2_update(
                        context=context,
                        status="failed",
                        detail=f"Phase 2 ended without a code block (iteration {context.iteration_count}, attempt {attempt + 1})."
                    )
                    self.logger.warning(f"Phase 2 consecutive failures: {context.phase2_consecutive_failures}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Phase 2 failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    continue
                context.phase2_consecutive_failures += 1
                self._record_phase2_update(
                    context=context,
                    status="failed",
                    detail=f"Phase 2 exception on final attempt (iteration {context.iteration_count}): {e}"
                )
                self.logger.warning(f"Phase 2 consecutive failures: {context.phase2_consecutive_failures}")
                return False
        
        return False

    def _record_phase2_update(self, context: PipelineContext, status: str, detail: str) -> None:
        """Record per-iteration Phase 2 completion updates for Telegram delivery."""
        updates = context.metadata.setdefault("phase2_updates", [])
        updates.append({
            "status": status,
            "iteration": context.iteration_count,
            "detail": detail,
        })

    def _summarize_phase2_goal(self, phase_input: str) -> Optional[str]:
        """
        Summarize the Phase 1/original plan content into a single sentence.
        This synchronization summary always uses the base model configured in config.yaml.
        """
        try:
            from ..utils.config import load_config

            cfg = load_config()
            provider = getattr(cfg.api, "preferred_provider", None) or None

            model = None
            if provider == "ollama":
                model = getattr(cfg.api, "local_model", None)
            elif provider and getattr(cfg.api, "models", None):
                model = cfg.api.models.get(provider)

            sync_runner = ModelRunner(provider=provider, model=model, config=self.config)

            request = ModelRequest(
                task_type=TaskType.PHASE2_GOAL_SUMMARY,
                prompt=phase_input,
                context={"phase_1_output": phase_input},
                max_tokens=180,
                temperature=0.2
            )

            response = sync_runner.run_model(request)
            if not response.success or not response.content:
                self.logger.warning(f"Phase 2 goal summary failed: {response.error}")
                return None

            summary = self._extract_code_block(response.content) or response.content
            summary = " ".join(summary.strip().splitlines()).strip()

            if summary and not summary.endswith((".", "!", "?")):
                summary = f"{summary}."

            self.logger.info("Phase 2 goal summary generated", summary_length=len(summary))
            return summary
        except Exception as e:
            self.logger.warning(f"Phase 2 goal summary exception: {e}")
            return None
    
    def _run_phase3(self, context: PipelineContext) -> bool:
        """
        Phase 3: Command Execution
        
        Execute the extracted commands by injecting all lines into the terminal at once.
        Reuse the same terminal session throughout the entire task.
        Terminal logs accumulate continuously.
        
        If command execution fails, re-run Phase 3 (up to 3 retries).
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Phase 3: Command Execution started")
        context.current_phase = PipelinePhase.PHASE3_COMMAND_EXECUTION
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not context.extracted_commands:
                    self.logger.error("Phase 3: No commands to execute")
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Phase 3: Retrying (attempt {attempt + 2}/{max_retries})")
                        continue
                    return False
                
                # Parse commands from the extracted code block
                commands = self._parse_commands(context.extracted_commands)
                
                if not commands:
                    self.logger.error("Phase 3: No valid commands parsed")
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Phase 3: Retrying (attempt {attempt + 2}/{max_retries})")
                        continue
                    return False
                
                self.logger.info(f"Phase 3: Executing {len(commands)} commands in batch")
                
                # Execute all commands in a single batch (maintaining same terminal session)
                result = self.terminal_history.execute_commands_batch(
                    commands, 
                    timeout=self.command_timeout
                )
                
                # Log result
                if result.get("success"):
                    self.logger.info("Phase 3: Batch execution succeeded")
                else:
                    self.logger.warning(f"Phase 3: Batch execution failed: {result.get('stderr', 'Unknown')}")
                
                # Update terminal log in context
                context.terminal_log = self.terminal_history.display_terminal_log(max_entries=1000)
                
                self.logger.info("Phase 3 completed successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Phase 3 failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    self.logger.warning(f"Phase 3: Retrying (attempt {attempt + 2}/{max_retries})")
                    continue
                return False
        
        return False
    
    def _run_phase4(self, context: PipelineContext) -> bool:
        """
        Phase 4: Log Evaluation and Re-execution Decision

        Send terminal logs to base model for evaluation.

        Returns:
            True if the Phase 4 output contains a code block (continue loop to Phase 2),
            False if no code block (proceed to Phase 5)
        """
        self.logger.info("Phase 4: Log Evaluation started")
        context.current_phase = PipelinePhase.PHASE4_LOG_EVALUATION

        try:
            # Get full terminal log
            full_terminal_log = self.terminal_history.display_terminal_log(max_entries=1000)

            # Create request for Phase 4
            request = ModelRequest(
                task_type=TaskType.PHASE4_LOG_EVALUATION,
                prompt=full_terminal_log,
                context={
                    "user_prompt": context.user_prompt,
                    "full_terminal_log_so_far": full_terminal_log,
                },
                max_tokens=4000,
                temperature=0.5
            )

            # Run model
            response = self.model_runner.run_model(request)

            if not response.success:
                self.logger.error(f"Phase 4 model execution failed: {response.error}")
                # Assume success to proceed to Phase 5
                return False

            context.phase4_output = response.content

            # Check if output contains a code block
            has_code_block = self._has_code_block(response.content)

            self.logger.info("Phase 4 completed",
                           has_code_block=has_code_block,
                           output_length=len(response.content))

            # If code block is present, the task failed - continue Phase 2-4 loop
            # If no code block, the task succeeded - proceed to Phase 5
            return has_code_block
            
        except Exception as e:
            self.logger.error(f"Phase 4 failed: {e}")
            # On error, proceed to Phase 5
            return False
    
    def _run_phase5(self, context: PipelineContext) -> bool:
        """
        Phase 5: Summary Generation and Display
        
        Generate human-readable summary of what was done and the result.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Phase 5: Summary Generation started")
        context.current_phase = PipelinePhase.PHASE5_SUMMARY_GENERATION
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get full terminal log
                full_terminal_log = self.terminal_history.display_terminal_log(max_entries=1000)
                
                # Create request for Phase 5
                request = ModelRequest(
                    task_type=TaskType.PHASE5_SUMMARY_GENERATION,
                    prompt=full_terminal_log,
                    context={
                        "user_prompt": context.user_prompt,
                        "full_terminal_log": full_terminal_log,
                    },
                    max_tokens=4000,
                    temperature=0.7
                )
                
                # Run model
                response = self.model_runner.run_model(request)
                
                if not response.success:
                    self.logger.error(f"Phase 5 model execution failed: {response.error}")
                    if attempt < max_retries - 1:
                        continue
                    return False
                
                # Extract and concatenate all code blocks
                summary = self._extract_all_code_blocks(response.content)
                
                if summary:
                    context.final_summary = summary
                    self.logger.info("Phase 5 completed successfully",
                                   summary_length=len(summary))
                    
                    # Display the summary
                    print("")
                    print(context.final_summary)
                    
                    # Send via Telegram if enabled
                    self._init_telegram()
                    if self._telegram_enabled:
                        self._send_via_telegram(summary)
                    
                    return True
                else:
                    self.logger.warning(f"Phase 5: No code block found in attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    return False
                    
            except Exception as e:
                self.logger.error(f"Phase 5 failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    continue
                return False
        
        return False
    
    def _extract_code_block(self, text: str) -> Optional[str]:
        """
        Extract code block from text.
        If multiple code blocks are present, use the last one.
        Supports any language specifier (bash, python, json, etc.) or no specifier.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            Extracted code block content or None if not found
        """
        # Pattern to match code blocks with any language specifier
        pattern = r'```(?:\w+)?\s*\n?(.*?)```'
        
        # Find all code blocks (non-greedy match)
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            # Use the last code block if multiple exist
            return matches[-1].strip()
        
        return None
    
    def _has_code_block(self, text: str) -> bool:
        """Check if text contains a code block"""
        pattern = r'```(?:\w+)?\s*\n?.*?```'
        return bool(re.search(pattern, text, re.DOTALL))
    
    def _has_failure_indicator(self, text: str) -> bool:
        """
        Check if text indicates command failure using multiple indicators.
        
        Uses weighted scoring based on:
        - Explicit failure keywords
        - Error patterns in terminal output
        - Command exit status indicators
        - Negative sentiment words
        
        Returns True only if failure score exceeds threshold.
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Explicit failure indicators (weight: 3)
        failure_keywords = [
            'failure', 'failed', 'error occurred', 'unsuccessful',
            'command failed', 'execution failed', 'task failed'
        ]
        
        # Terminal error patterns (weight: 2)
        error_patterns = [
            'exit code:', 'returned non-zero', 'command not found',
            'permission denied', 'no such file', 'syntax error',
            'segmentation fault', 'core dumped', 'killed', 'terminated'
        ]
        
        # Negative indicators (weight: 1)
        negative_indicators = [
            'error', 'warning', 'abort', 'fatal', 'critical',
            'cannot', 'unable', 'not found', 'invalid'
        ]
        
        # Success indicators that override failure (weight: -5)
        success_indicators = [
            'success', 'completed successfully', 'done', 'finished',
            'task completed', 'execution successful', 'all commands executed'
        ]
        
        score = 0
        
        # Check failure keywords
        for keyword in failure_keywords:
            if keyword in text_lower:
                score += 3
                self.logger.debug(f"Failure indicator found: '{keyword}' (+3)")
        
        # Check error patterns
        for pattern in error_patterns:
            if pattern in text_lower:
                score += 2
                self.logger.debug(f"Error pattern found: '{pattern}' (+2)")
        
        # Check negative indicators
        for indicator in negative_indicators:
            if indicator in text_lower:
                score += 1
                self.logger.debug(f"Negative indicator found: '{indicator}' (+1)")
        
        # Check success indicators (these reduce score)
        for indicator in success_indicators:
            if indicator in text_lower:
                score -= 5
                self.logger.debug(f"Success indicator found: '{indicator}' (-5)")
        
        # Threshold: score >= 3 indicates failure
        is_failure = score >= 3
        
        self.logger.info(f"Failure analysis complete",
                        score=score,
                        threshold=3,
                        is_failure=is_failure,
                        text_preview=text[:100] + "..." if len(text) > 100 else text)
        
        return is_failure
    
    def _extract_all_code_blocks(self, text: str) -> Optional[str]:
        """
        Extract and concatenate all code blocks from text.
        
        Args:
            text: Text containing code blocks
            
        Returns:
            Concatenated code block content or None if not found
        """
        pattern = r'```(?:\w+)?\s*\n?(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            # Concatenate all code blocks
            return "\n\n".join(block.strip() for block in matches)
        
        return None
    
    def _parse_commands(self, code_block: str) -> List[str]:
        """
        Parse commands from a code block.
        
        Args:
            code_block: Code block content
            
        Returns:
            List of individual commands
        """
        commands = []
        
        # Split by newlines and filter
        lines = code_block.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Skip markdown formatting remnants
            if line.startswith('```'):
                continue
            
            commands.append(line)
        
        return commands
    
    def _get_os_info(self) -> str:
        """Get OS information for CLI context"""
        try:
            import os
            
            system = platform.system()
            release = platform.release()
            version = platform.version()
            machine = platform.machine()
            
            # Get shell info for Unix-like systems
            shell = os.environ.get('SHELL', 'Unknown')
            
            if system == "Linux":
                try:
                    with open('/etc/os-release', 'r') as f:
                        lines = f.readlines()
                    distro_info = {}
                    for line in lines:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            distro_info[key] = value.strip('"')
                    
                    distro_name = distro_info.get('NAME', 'Unknown Linux')
                    distro_version = distro_info.get('VERSION', '')
                    os_info = f"{distro_name} {distro_version} ({system} {release} {machine})"
                except:
                    os_info = f"Linux {release} {machine}"
            
            elif system == "Darwin":
                os_info = f"macOS {release} {machine}"
            
            elif system == "Windows":
                os_info = f"Windows {release} {machine}"
            
            else:
                os_info = f"{system} {release} {machine}"
            
            if system in ["Linux", "Darwin"]:
                os_info += f" (Shell: {shell})"
            
            return os_info
            
        except Exception as e:
            self.logger.warning(f"Failed to get OS info: {e}")
            return "Unknown OS"


def get_five_phase_engine(config: Optional[Dict[str, Any]] = None) -> FivePhaseEngine:
    """Get 5-Phase Pipeline Engine instance"""
    return FivePhaseEngine(config)
