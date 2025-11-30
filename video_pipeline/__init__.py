"""
Video generation pipeline package using Gemini text/image models and Veo video generation.
"""

from .config import (
    PipelineConfig,
    describe_api_mode,
    get_default_config,
    get_genai_client,
    is_real_api_enabled,
    use_fake_genai,
)
from .fake_genai import FakeGenaiClient

__all__ = [
    "PipelineConfig",
    "get_default_config",
    "get_genai_client",
    "is_real_api_enabled",
    "use_fake_genai",
    "describe_api_mode",
    "FakeGenaiClient",
]
