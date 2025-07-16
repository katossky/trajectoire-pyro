import os
import asyncio
import argparse
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.teams import RoundRobinGroupChat

_OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ------------------------------------------------------------
# Tool layer – all exported GitHub helpers
# ------------------------------------------------------------

from .tools import (
    list_directories,
    list_files,
    read_file,
    create_directory,
    write_file,
    list_issues,
    get_issue_body,
    create_issue,
    comment_issue,
    close_issue,
    list_existing_labels,
    get_labels,
    add_label,
    remove_label,
)

# ------------------------------------------------------------
# System prompt (markdown file kept under prompts/owner.md)
# ------------------------------------------------------------

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "owner.md")
if not os.path.exists(_PROMPT_PATH):
    raise FileNotFoundError("Expected system prompt at prompts/owner.md – not found")

with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    SYSTEM_MSG = _f.read()

# ------------------------------------------------------------
# AutoGen agent configuration
# ------------------------------------------------------------

TOOLS = [
    list_directories,
    list_files,
    read_file,
    create_directory,
    write_file,
    list_issues,
    get_issue_body,
    create_issue,
    comment_issue,
    close_issue,
    list_existing_labels,
    get_labels,
    add_label,
    remove_label,
]

model_client = OpenAIChatCompletionClient(
    model="moonshotai/kimi-k2",
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

agent = AssistantAgent(
    name = "owner",
    model_client = model_client,
    system_message = SYSTEM_MSG,
    # system_message = "You are product owner of this project. Write TERMINATE when task is done.",
    tools = TOOLS,
    # reflect_on_tool_use=True,
    model_client_stream=True,
)

team = RoundRobinGroupChat(
    [agent],
    termination_condition = TextMentionTermination("TERMINATE") | MaxMessageTermination(100),
)

# ------------------------------------------------------------
# Entry point – run once or looped in CI
# ------------------------------------------------------------

async def run(task):
    await Console(
        team.run_stream(task=task),
        output_stats=True
    )

def main():

    parser = argparse.ArgumentParser(
        prog="owner.py",
        description="Run the Owner agent",
    )

    parser.add_argument(
        "-t",
        "--task",
        metavar="TEXT",
        type=str,
        default=None,
        help="Specific task to give to the Owner agent",
    )
    
    args = parser.parse_args()

    asyncio.run(run(task = args.task))

if __name__ == "__main__":

    main()