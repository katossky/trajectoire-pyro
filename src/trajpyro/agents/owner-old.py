import os
import asyncio
import argparse
from autogen_agentchat.agents import AssistantAgent
# from clients import KimiOpenRouterClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    ThoughtEvent, ModelClientStreamingChunkEvent, ToolCallExecutionEvent,
    ToolCallRequestEvent, TextMessage
)
# from autogen_ext.models.llama_cpp import LlamaCppChatCompletionClient
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.teams import RoundRobinGroupChat

_OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ------------------------------------------------------------
# Tool layer – all exported GitHub helpers
# ------------------------------------------------------------

from tools import (
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
    # append_readme,
    # create_readme_section,
]

# model_client = LlamaCppChatCompletionClient(
#     model_path="~/.cache/huggingface/hub/unsloth/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q6_K.gguf",  # or repo_id/filename
#     # n_gpu_layers=-1,  # put all layers on GPU (-1) or tweak per your card
#     # n_ctx=8192,
# )

model_client = OpenAIChatCompletionClient(
    model="moonshotai/kimi-k2",
    base_url="https://openrouter.ai/api/v1",
    api_key=_OPENROUTER_API_KEY,
    # max_tokens = 400,
    logit_bias ={
        # 3185:-100 # me
        # 163595:-100, # <|tool_calls_section_begin|>
        # 163596:-100, # <|tool_calls_section_end|>
        # 163597:-100, # <|tool_call_begin|>
        # 163599:-100, # <|tool_call_end|>
    },
    model_info = {
        "context_window":    131_072,
        "max_output_tokens": 16_384,
        # Interface capabilities
        "supports_stream":    True,
        "function_calling":   True,
        "json_output":        True, # False, # error in OpenRouter otherwise
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
    tools = TOOLS,
    reflect_on_tool_use=True,
    model_client_stream=True,
)

team = RoundRobinGroupChat(
    [agent],
    # Stop only when the magic word shows up – **not** on any plain TextMessage.
    termination_condition = TextMentionTermination("TERMINATE") | MaxMessageTermination(100),
)

# ------------------------------------------------------------
# Entry point – run once or looped in CI
# ------------------------------------------------------------

async def main(task):
    await Console(
        team.run_stream(task=task),
        output_stats=True
    )

# async def main(task):
#     is_streaming = False
#     async for ev in team.run_stream(task = task):
#         match ev:
#             case TaskResult():
#                 print("\n----- ✅ task finished ------\n")
#                 print(f"stop_reason: {ev.stop_reason}")
#             case TextMessage() | ThoughtEvent():
#                 if not is_streaming :
#                     content = ev.to_text()
#                     if content != "" :
#                         print(f"\n----- 💬 message from {ev.source} ------\n")
#                         print(ev.to_text())
#                 else :
#                     print("\n")
#                     is_streaming = False
#             case ModelClientStreamingChunkEvent():
#                 if not is_streaming :
#                     print(f"\n----- 💬 message from {ev.source} ------\n")
#                     is_streaming = True
#                 print(ev.to_text(), end="", flush=True)   # each token
#             case ToolCallRequestEvent() :
#                 print(f"\n----- 🔧 calling {', '.join([ f.name for f in ev.content])} ------\n")
#                 print(ev.to_text())
#             case ToolCallExecutionEvent():
#                 print(f"\n----- 🔧 return from {', '.join([ f.name for f in ev.content])} ------\n")
#                 print(ev.to_text())
#             case _:
#                 if is_streaming :
#                     print("\n")
#                     is_streaming = False
#                 print(f"\n----- ❓ Unknown event of type {ev.type} ------\n")
#                 print(ev.to_text())
#             # you can handle more event types here if you need

if __name__ == "__main__":

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

    asyncio.run(main(task = args.task))