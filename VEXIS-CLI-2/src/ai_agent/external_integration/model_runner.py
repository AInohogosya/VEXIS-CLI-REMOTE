"""
Model Runner for VEXIS-CLI-2 AI Agent System
Multi-Provider Support: 13+ AI providers available
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from .multi_provider_vision_client import MultiProviderVisionAPIClient, APIRequest, APIProvider
from ..utils.exceptions import ValidationError
from ..utils.logger import get_logger
from ..utils.config import load_config


class TaskType(Enum):
    """Task types for 5-Phase CLI Architecture"""
    PHASE1_COMMAND_SUGGESTION = "phase1_command_suggestion"
    PHASE2_COMMAND_EXTRACTION = "phase2_command_extraction"
    PHASE4_LOG_EVALUATION = "phase4_log_evaluation"
    PHASE5_SUMMARY_GENERATION = "phase5_summary_generation"


@dataclass
class ModelRequest:
    """Model request structure"""
    task_type: TaskType
    prompt: str
    image_data: Optional[bytes] = None
    image_format: str = "PNG"
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    max_tokens: int = 5000
    temperature: float = 1.0
    timeout: int = 30


@dataclass
class ModelResponse:
    """Model response structure"""
    success: bool
    content: str
    task_type: TaskType
    model: str
    provider: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    latency: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PromptTemplate:
    """Prompt template manager"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load prompt templates for 5-Phase CLI Architecture"""
        return {
            TaskType.PHASE1_COMMAND_SUGGESTION.value: '''I have received the instruction: "{user_prompt}". What commands should I run to carry this out? Please tell me. I can only use terminal commands, so do not suggest GUI operations. The OS I am using is {os_info}.''',

            TaskType.PHASE2_COMMAND_EXTRACTION.value: '''Please look at this: {phase_1_output}. This is a relatively long text with many explanations, but please put all the necessary commands into a single code block. You may use only one code block.''',

            TaskType.PHASE4_LOG_EVALUATION.value: '''I executed the commands to carry out the instruction {user_prompt}. This resulted in the following log: {full_terminal_log_so_far} However, since I am a beginner, I do not know if it succeeded or failed. IMPORTANT: If the task failed, you MUST include the word "failure" somewhere in your response. If it succeeded, simply confirm success without using the word "failure".''',

            TaskType.PHASE5_SUMMARY_GENERATION.value: '''I received the instruction {user_prompt} and have been executing commands like this to carry it out. {full_terminal_log} Now, I need to explain to the person who gave the instruction what I did, how I did it, and what the results were. Please summarize this information and output it inside a code block.''',
        }

    def get_template(self, task_type: TaskType) -> str:
        """Get template for task type"""
        return self.templates.get(task_type.value, "")


class ModelRunner:
    """CLI Architecture Model Runner: Ollama Cloud Models"""

    # Valid Ollama model names
    DEFAULT_OLLAMA_MODEL = "llama3.2:latest"
    DEFAULT_GOOGLE_MODEL = "gemini-3.1-pro-preview"

    def __init__(self, provider: str = None, model: str = None, config: Optional[Dict[str, Any]] = None, auto_install_sdks: bool = False):
        # Direct provider and model from runtime arguments
        self.provider = provider
        self.model = model
        
        # Fallback to config if not provided
        self.config = config or load_config().api.__dict__
        self.logger = get_logger(__name__)
        
        # Initialize multi-provider vision client with SDK installation support
        self.vision_client = MultiProviderVisionAPIClient(self.config, auto_install_sdks=auto_install_sdks)
        self.prompt_template = PromptTemplate()

        self.logger.info(
            "Model runner initialized",
            provider=self.provider,
            model=self.model,
        )

    def run_model(self, request: ModelRequest) -> ModelResponse:
        """Run AI model for CLI Architecture"""
        start_time = time.time()

        try:
            # Validate request
            self._validate_request(request)

            # Format prompt
            prompt = self._format_prompt(request)

            # Get system instructions for API request
            system_instructions = self._get_system_instructions(request.task_type)

            # Use runtime provider and model if provided, otherwise fallback to settings
            if self.provider and self.model:
                provider_name = self.provider
                model_name = self.model
            else:
                # Fallback to settings for backward compatibility
                from ..utils.settings_manager import get_settings_manager
                settings = get_settings_manager()
                provider_name = settings.get_preferred_provider()
                model_name = settings.get_model(provider_name)

            if not provider_name:
                raise ValidationError("No provider configured. Please select a provider first.")

            if not model_name:
                raise ValidationError(f"No model configured for provider '{provider_name}'. Please select a model first.")

            # Create API request with user's exact selection
            api_request = APIRequest(
                prompt=prompt,
                image_data=request.image_data,
                image_format=request.image_format,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                model=model_name,
                provider=provider_name,
                system_instruction=system_instructions
            )

            # Make API call
            api_response = self.vision_client.generate_response(api_request)

            # Create model response
            model_response = ModelResponse(
                success=api_response.success,
                content=api_response.content,
                task_type=request.task_type,
                model=api_response.model or model_name,
                provider=api_response.provider or provider_name,
                tokens_used=api_response.tokens_used,
                cost=api_response.cost,
                latency=time.time() - start_time,
                error=api_response.error,
            )

            if api_response.success:
                self.logger.info(
                    "Model execution successful",
                    task_type=request.task_type.value,
                    model=model_response.model,
                    latency=model_response.latency,
                )
            else:
                self.logger.error(
                    "Model execution failed",
                    task_type=request.task_type.value,
                    error=model_response.error,
                )
                
                # Enhanced error handling for authentication issues
                if "Authentication required" in model_response.error:
                    try:
                        from ..utils.ollama_error_handler import handle_ollama_error
                        context = {
                            'model_name': model_response.model,
                            'operation': 'model_execution'
                        }
                        handle_ollama_error(model_response.error, context, display_to_user=True)
                        
                        # Prompt user to sign in
                        import sys
                        if sys.stdin.isatty():  # Only prompt if running in terminal
                            try:
                                choice = input("\nWould you like to sign in to Ollama now? (y/n): ").lower().strip()
                                if choice in ['y', 'yes']:
                                    import subprocess
                                    print("\n🔐 Opening Ollama sign-in...")
                                    result = subprocess.run(["ollama", "signin"], capture_output=False, text=True)
                                    if result.returncode == 0:
                                        print("✓ Sign-in initiated. Please complete it in your browser.")
                                        print("Then try running your command again.")
                                    else:
                                        print("✗ Failed to initiate sign-in.")
                            except (KeyboardInterrupt, EOFError):
                                print("\nOperation cancelled.")
                    except ImportError:
                        pass  # Fallback to just logging the error

            return model_response

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Model execution failed: {e}")
            return ModelResponse(
                success=False,
                content="",
                task_type=request.task_type,
                model="",
                provider="",
                latency=time.time() - start_time,
                error=str(e),
            )

    def _validate_request(self, request: ModelRequest):
        """Validate model request"""
        if not request.prompt:
            raise ValidationError("Prompt cannot be empty", "prompt", request.prompt)

        if request.max_tokens < 1 or request.max_tokens > 7000:
            raise ValidationError("Invalid max_tokens", "max_tokens", request.max_tokens)

        if not (0.0 <= request.temperature <= 2.0):
            raise ValidationError("Invalid temperature", "temperature", request.temperature)

        if request.task_type not in TaskType:
            raise ValidationError("Invalid task type", "task_type", request.task_type)

    def _format_prompt(self, request: ModelRequest) -> str:
        """Format prompt based on task type and context"""
        template = self.prompt_template.get_template(request.task_type)

        format_vars = {
            "instruction": request.prompt,
            "task_description": request.prompt,
            "user_prompt": request.prompt,
        }

        # Add context variables if available (e.g., phase_1_output for Phase 2)
        if request.context:
            format_vars.update(request.context)

        format_vars.setdefault("os_info", "Unknown OS")

        try:
            formatted_prompt = template.format(**format_vars)
            
            # Add system instructions for better AI behavior
            system_instructions = self._get_system_instructions(request.task_type)
            if system_instructions:
                # For providers that support system instructions, we'll set them in the config
                # For others, we prepend to the prompt
                if hasattr(request, 'parameters') and request.parameters:
                    request.parameters['system_instruction'] = system_instructions
                else:
                    # Prepend system instructions to prompt for providers that don't support separate system messages
                    formatted_prompt = f"{system_instructions}\n\n{formatted_prompt}"
            
            return formatted_prompt
        except KeyError as e:
            self.logger.warning(f"Template variable missing: {e}")
            return request.prompt
        except Exception as e:
            self.logger.error(f"Template formatting error: {e}")
            return request.prompt

    def _get_system_instructions(self, task_type: TaskType) -> str:
        """Get system instructions for better AI behavior"""
        base_instructions = """# VEXIS-CLI-2 AI Agent System Instructions

You are operating as part of the VEXIS-CLI-2 automation system. Your responses directly impact system execution and user experience.

## Behavioral Guidelines
1. **Precision Over Verbosity** - Be exact and concise
2. **Context Awareness** - Always consider previous actions and current state
3. **Error Resilience** - Handle failures gracefully and suggest alternatives
4. **Safety First** - Never suggest destructive commands without clear warnings
5. **User Intent Focus** - Stay focused on accomplishing the user's original goal

## Response Standards
- Use clear, unambiguous language
- Provide specific, actionable outputs
- Avoid conversational filler or unnecessary explanations
- Maintain consistency with previous interactions
- Respect the established workflow and command patterns

## Quality Assurance
- Double-check command syntax before outputting
- Verify file paths and parameters are valid
- Consider edge cases and potential failure points
- Ensure outputs match the expected format exactly"""
        
        return base_instructions

    def install_missing_sdks(self, providers: Optional[List[str]] = None, interactive: bool = True) -> Dict[str, bool]:
        """Install missing SDKs for specified providers"""
        return self.vision_client.install_missing_sdks(providers, interactive)
    
    def show_sdk_status(self, providers: Optional[List[str]] = None):
        """Show SDK installation status"""
        self.vision_client.show_sdk_status(providers)


def get_model_runner(provider: str = None, model: str = None) -> ModelRunner:
    """Get model runner instance with optional provider and model"""
    # Create instance with runtime provider and model
    return ModelRunner(provider=provider, model=model)
