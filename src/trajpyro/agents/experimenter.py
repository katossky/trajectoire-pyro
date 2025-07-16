
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.ui import Console  


from typing_extensions import Annotated

import asyncio

model_client = OpenAIChatCompletionClient(
    model="phi-4-reasoning-plus",               # any label you like
    base_url="http://host.docker.internal:8080/v1",  # 0.0.0.0:8080 from the container
    api_key="local-phi4",                       # must be non-empty, value ignored
    model_client_stream=True,
    model_info = {
        "context_window":    32_000,
        "max_output_tokens":  8_192,
        "supports_stream":     True,
        "vision":             False,
        "function_calling":    True,
        "family" :            "phi",
        "json_output":        False,
        "structured_output" : False,
    }
)

def add_numbers(
    a: Annotated[int, "first element to add"],
    b: Annotated[int, "second element to add"]
) -> int:   # signature = parameters schema
    """Add two integers."""
    return a + b

agent = AssistantAgent(
    name="experimenter",
    model_client=model_client,
    tools = [add_numbers],
)

async def main():
    await Console(                       # <- hands the generator to Console
        agent.run_stream(task="What is 23 + 19?"),
        output_stats=True                # nice summary at the end (optional)
    )

if __name__ == "__main__":
    asyncio.run(main())