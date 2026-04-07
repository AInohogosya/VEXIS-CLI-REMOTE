"""
OpenRouter LLM Client Adapter

Implements BaseLLM interface for OpenRouter API.
Uses OpenAI SDK with OpenRouter's custom base URL.

Installation:
    pip install openai

Environment Variables:
    OPENROUTER_API_KEY: API key for OpenRouter API
"""

import os
import time
from typing import Optional, Dict, Any, List, Iterator, AsyncIterator

from .base import (
    BaseLLM, ProviderType, GenerationConfig, LLMResponse,
    ModelInfo, ResponseFormat, _estimate_cost
)

# Import OpenAI SDK
try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenRouterLLMClient(BaseLLM):
    """
    OpenRouter LLM client using OpenAI SDK with custom base URL.
    
    This adapter implements the BaseLLM interface for OpenRouter models,
    which uses OpenAI-compatible API but with different endpoint and models.
    
    Parameter Mapping (direct - OpenRouter uses OpenAI-compatible naming):
        - max_tokens -> max_tokens
        - temperature -> temperature (0.0 - 2.0)
        - top_p -> top_p (0.0 - 1.0)
        - stop_sequences -> stop (list of strings)
    
    Usage:
        client = OpenRouterClient(api_key="your-key")
        response = client.generate("Explain quantum computing", config=config)
    
    Popular Models (as of 2026):
        - google/gemini-flash-1.5:free: Free Gemini model
        - google/gemini-pro-1.5: Advanced Gemini
        - anthropic/claude-3.5-sonnet: Claude 3.5 Sonnet
        - openai/gpt-4o: GPT-4o
        - meta-llama/llama-3.1-70b-instruct: Llama 3.1 70B
        - qwen/qwen3.6-plus:free: Free Qwen model
    """

    # Default model to use
    DEFAULT_MODEL = "google/gemini-flash-1.5:free"

    # Model context windows (approximate)
    MODEL_CONTEXT_WINDOWS = {
        "google/gemini-flash-1.5:free": 1_048_576,
        "google/gemini-pro-1.5": 2_097_152,
        "anthropic/claude-3.5-sonnet": 200_000,
        "openai/gpt-4o": 128_000,
        "meta-llama/llama-3.1-70b-instruct": 128_000,
        "qwen/qwen3.6-plus:free": 32_768,
    }

    # Max output tokens per model
    MODEL_MAX_TOKENS = {
        "google/gemini-flash-1.5:free": 8_192,
        "google/gemini-pro-1.5": 8_192,
        "anthropic/claude-3.5-sonnet": 8_192,
        "openai/gpt-4o": 4_096,
        "meta-llama/llama-3.1-70b-instruct": 8_192,
        "qwen/qwen3.6-plus:free": 32_768,
    }

    # Vision-capable models
    VISION_MODELS = {
        "google/gemini-flash-1.5:free", "google/gemini-pro-1.5",
        "anthropic/claude-3.5-sonnet", "openai/gpt-4o",
    }

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key. If not provided, uses OPENROUTER_API_KEY
                    environment variable.
            **kwargs: Additional configuration options
                - base_url: Custom API base URL (defaults to OpenRouter)
                - timeout: Request timeout in seconds
                - max_retries: Number of retries for failed requests
        """
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._config = kwargs
        self._client = None
        self._async_client = None
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required. "
                "Install with: pip install openai"
            )

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENROUTER
    
    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    def _initialize_client(self) -> None:
        """Initialize OpenRouter client using OpenAI SDK"""
        if not self._api_key:
            raise ValueError(
                "OpenRouter API key is required. Provide it as an argument or "
                "set OPENROUTER_API_KEY environment variable."
            )
        
        client_kwargs = {
            "api_key": self._api_key,
            "timeout": self._config.get("timeout", 60),
            "max_retries": self._config.get("max_retries", 2),
        }
        
        # Set OpenRouter's base URL by default
        if "base_url" not in self._config:
            client_kwargs["base_url"] = "https://openrouter.ai/api/v1"
        else:
            client_kwargs["base_url"] = self._config["base_url"]
        
        self._client = OpenAI(**client_kwargs)
        self._async_client = AsyncOpenAI(**client_kwargs)

    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        images: Optional[List[Any]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using OpenRouter API.
        
        Args:
            prompt: The input prompt
            config: Generation configuration
            images: List of images (for vision models)
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse with generated content and metadata
        """
        if not self._client:
            self._initialize_client()
        
        config = config or GenerationConfig()
        start_time = time.time()
        
        try:
            # Get system instruction from config
            system_instruction = config.system_instruction if config else None
            
            # Prepare messages using helper method
            messages = self._build_messages(
                prompt=prompt,
                system_instruction=system_instruction,
                images=images,
                model=config.model if config else None
            )
            
            # Prepare generation parameters
            if hasattr(config, 'extra_params') and 'model' in config.extra_params:
                model = config.extra_params['model']
            
            model = config.model or self.default_model
            if hasattr(config, 'extra_params') and 'model' in config.extra_params:
                model = config.extra_params['model']
            
            generation_params = {
                "model": model,
                "messages": messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }
            
            if config.top_p is not None:
                generation_params["top_p"] = config.top_p
            if config.stop_sequences:
                generation_params["stop"] = config.stop_sequences
            
            # Add any additional kwargs
            generation_params.update(kwargs)
            
            # Make the API call
            response = self._client.chat.completions.create(**generation_params)
            
            # Extract response data
            content = response.choices[0].message.content
            model = response.model
            usage = response.usage
            
            # Calculate cost and latency
            latency = time.time() - start_time
            cost = _estimate_cost(
                provider=ProviderType.OPENROUTER,
                model=model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0
            )
            
            return LLMResponse(
                success=True,
                content=content,
                model=model,
                provider="openrouter",
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                tokens_used=usage.total_tokens if usage else 0,
                cost=cost,
                latency=latency,
                finish_reason=response.choices[0].finish_reason if response.choices else None
            )
            
        except Exception as e:
            return LLMResponse(
                success=False,
                content="",
                model=config.model or self.default_model,
                provider="openrouter",
                error=str(e),
                latency=time.time() - start_time
            )

    def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Generate streaming text using OpenRouter API.
        
        Args:
            prompt: The input prompt
            config: Generation configuration
            **kwargs: Additional generation parameters
            
        Yields:
            Chunks of generated text
        """
        if not self._client:
            self._initialize_client()
        
        config = config or GenerationConfig()
        
        try:
            # Get system instruction from config
            system_instruction = config.system_instruction if config else None
            
            # Prepare messages using helper method
            messages = self._build_messages(
                prompt=prompt,
                system_instruction=system_instruction,
                model=config.model if config else None
            )
            
            model = config.model or self.default_model
            if hasattr(config, 'extra_params') and 'model' in config.extra_params:
                model = config.extra_params['model']
            
            generation_params = {
                "model": model,
                "messages": messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "stream": True,
            }
            
            if config.top_p is not None:
                generation_params["top_p"] = config.top_p
            if config.stop_sequences:
                generation_params["stop"] = config.stop_sequences
            
            # Add any additional kwargs
            generation_params.update(kwargs)
            
            # Make streaming API call
            stream = self._client.chat.completions.create(**generation_params)
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"[ERROR] {str(e)}"

    async def generate_async(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        images: Optional[List[Any]] = None,
        **kwargs
    ) -> LLMResponse:
        """Async version of generate()"""
        if not self._async_client:
            self._initialize_client()
        
        config = config or GenerationConfig()
        start_time = time.time()
        
        try:
            # Get system instruction from config
            system_instruction = config.system_instruction if config else None
            
            # Prepare messages using helper method
            messages = self._build_messages(
                prompt=prompt,
                system_instruction=system_instruction,
                images=images,
                model=config.model if config else None
            )
            
            # Prepare generation parameters
            if hasattr(config, 'extra_params') and 'model' in config.extra_params:
                model = config.extra_params['model']
            
            model = config.model or self.default_model
            if hasattr(config, 'extra_params') and 'model' in config.extra_params:
                model = config.extra_params['model']
            
            generation_params = {
                "model": model,
                "messages": messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }
            
            if config.top_p is not None:
                generation_params["top_p"] = config.top_p
            if config.stop_sequences:
                generation_params["stop"] = config.stop_sequences
            
            generation_params.update(kwargs)
            
            # Make async API call
            response = await self._async_client.chat.completions.create(**generation_params)
            
            # Extract response data
            content = response.choices[0].message.content
            model = response.model
            usage = response.usage
            
            latency = time.time() - start_time
            cost = _estimate_cost(
                provider=ProviderType.OPENROUTER,
                model=model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0
            )
            
            return LLMResponse(
                success=False,
                content=content,
                model=model,
                provider="openrouter",
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                tokens_used=usage.total_tokens if usage else 0,
                cost=cost,
                latency=latency,
                finish_reason=response.choices[0].finish_reason if response.choices else None
            )
            
        except Exception as e:
            return LLMResponse(
                success=False,
                content="",
                model=config.model or self.default_model,
                provider="openrouter",
                error=str(e),
                latency=time.time() - start_time
            )

    async def generate_stream_async(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Async streaming version of generate()"""
        if not self._async_client:
            self._initialize_client()
        
        config = config or GenerationConfig()
        
        try:
            # Get system instruction from config
            system_instruction = config.system_instruction if config else None
            
            # Prepare messages using helper method
            messages = self._build_messages(
                prompt=prompt,
                system_instruction=system_instruction,
                model=config.model if config else None
            )
            
            model = config.model or self.default_model
            if hasattr(config, 'extra_params') and 'model' in config.extra_params:
                model = config.extra_params['model']
            
            generation_params = {
                "model": model,
                "messages": messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "stream": True,
            }
            
            if config.top_p is not None:
                generation_params["top_p"] = config.top_p
            if config.stop_sequences:
                generation_params["stop"] = config.stop_sequences
            
            generation_params.update(kwargs)
            
            stream = await self._async_client.chat.completions.create(**generation_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"[ERROR] {str(e)}"

    def get_models(self) -> List[ModelInfo]:
        """
        Get available models from OpenRouter.
        
        Returns:
            List of ModelInfo objects
        """
        if not self._client:
            self._initialize_client()
        
        try:
            
            models = []
            for model in response.data:
                model_info = ModelInfo(
                    id=model.id,
                    name=model.id,
                    description=getattr(model, 'description', ''),
                    context_length=self.MODEL_CONTEXT_WINDOWS.get(model.id, None),
                    max_tokens=self.MODEL_MAX_TOKENS.get(model.id, None),
                    pricing=getattr(model, 'pricing', {}),
                    vision_support=model.id in self.VISION_MODELS
                )
                models.append(model_info)
            
            return models
            
        except Exception as e:
            # Fallback to basic model list
            return [
                ModelInfo(
                    id="google/gemini-flash-1.5:free",
                    name="Google Gemini Flash 1.5 (Free)",
                    description="Free Gemini model",
                    context_length=1_048_576,
                    max_tokens=8_192,
                    vision_support=True
                ),
                ModelInfo(
                    id="qwen/qwen3.6-plus:free",
                    name="Qwen 3.6 Plus (Free)",
                    description="Free Qwen model",
                    context_length=32_768,
                    max_tokens=32_768,
                    vision_support=False
                )
            ]

    def list_models(self) -> List[ModelInfo]:
        """Alias for get_models() for compatibility"""
        return self.get_models()

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            ModelInfo object or None if not found
        """
        models = self.get_models()
        for model in models:
            if model.id == model_id:
                return model
        return None

    def _supports_vision(self, model: str) -> bool:
        """Check if model supports vision"""
        return model in self.VISION_MODELS

    def _build_messages(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        images: Optional[List[Any]] = None,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Build messages array with optional system instruction and images"""
        messages = []

        # Add system message if provided
        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction
            })

        # Build user message
        if images and self._supports_vision(model or self.default_model):
            content = [{"type": "text", "text": prompt}]

            for img in images:
                if hasattr(img, 'save'):  # PIL Image
                    import io
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_bytes = img_bytes.getvalue()
                    import base64
                    img_b64 = base64.b64encode(img_bytes).decode()
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                    })
                else:
                    # Assume bytes
                    import base64
                    img_b64 = base64.b64encode(img).decode()
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                    })

            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})

        return messages

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count tokens for text using OpenRouter's tokenizer.
        
        Note: This is an approximation since OpenRouter doesn't provide
        a public tokenizer. Uses OpenAI's tiktoken as fallback.
        """
        try:
            # Try to use tiktoken (OpenAI's tokenizer)
            import tiktoken
            
            # Use GPT-4 tokenizer as reasonable approximation
            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """
        Estimate cost for a given request.
        
        OpenRouter pricing varies by model. This provides estimates for common models.
        """
        # Pricing per 1M tokens (approximate)
        pricing = {
            "google/gemini-flash-1.5:free": {"prompt": 0.0, "completion": 0.0},  # Free tier
            "google/gemini-pro-1.5": {"prompt": 0.625, "completion": 2.5},
            "anthropic/claude-3.5-sonnet": {"prompt": 3.0, "completion": 15.0},
            "openai/gpt-4o": {"prompt": 5.0, "completion": 15.0},
            "meta-llama/llama-3.1-70b-instruct": {"prompt": 0.9, "completion": 0.9},
            "qwen/qwen3.6-plus:free": {"prompt": 0.0, "completion": 0.0},  # Free tier
        }
        
        model_pricing = pricing.get(model, {"prompt": 1.0, "completion": 1.0})
        
        prompt_cost = (prompt_tokens / 1_000_000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * model_pricing["completion"]
        
        return prompt_cost + completion_cost
