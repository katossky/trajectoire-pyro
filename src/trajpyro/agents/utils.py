import os
from autogen_ext.models.openai import OpenAIChatCompletionClient

_OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_client(what="moonshotai/kimi-k2") -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
    model=what,
    base_url="https://openrouter.ai/api/v1",
    api_key=_OPENROUTER_API_KEY,
    model_info = {
        "context_window":    131_072,
        "max_output_tokens": 16_384,
        # Interface capabilities
        "supports_stream":    True,
        "function_calling":   True,
        "json_output":        False,
        "structured_output":  False,
        # Modalities & taxonomy
        "vision":             False,
        "family":             "Kimi",
    }
)

def get_prompt(role : str) -> str:
    os.path.join("src", "trajpyro", "agents", "prompts", f"{role}.md")