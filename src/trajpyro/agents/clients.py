import re
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import AssistantMessage
from autogen_core import FunctionCall

_SECTION = re.compile(
    r"<\|tool_calls_section_begin\|>(.*?)<\|tool_calls_section_end\|>",
    re.S,
)
_CALL = re.compile(
    r"<\|tool_call_begin\|>\s*(?P<id>[\w\.]+:\d+)\s*"
    r"<\|tool_call_argument_begin\|>\s*(?P<args>{.*?})\s*"
    r"<\|tool_call_end\|>",
    re.S,
)

class KimiOpenRouterClient(OpenAIChatCompletionClient):
    """Convert Kimi‑style sentinels to OpenAI `tool_calls` objects."""

    def _parse_calls(self, text: str) -> list[FunctionCall] | None:
        m = _SECTION.search(text)
        if not m:
            return None                     # no tool calls in this chunk
        body = m.group(1)
        calls: list[FunctionCall] = []
        for hit in _CALL.finditer(body):
            call_id = hit["id"]
            args    = hit["args"].strip()
            # heuristic: function name is whatever comes after the last dot
            fn_name = call_id.split(".")[-1].split(":")[0]
            calls.append(FunctionCall(id=call_id, name=fn_name, arguments=args))
        return calls


    # ------------------------------------------------------------
    async def message_retrieval(self, resp):
        raw_msg = super().message_retrieval(resp)[0]   # dict-like message
        tool_calls = self._parse_calls(raw_msg.get("content", "") or "")
        if tool_calls is None:
            return [raw_msg]                           # plain text, nothing to do

        # Build a *structured* assistant message AutoGen can route to tools
        struct_msg = AssistantMessage(
            source = raw_msg.get("source", "assistant"),
            content = tool_calls,                      # <-- list[FunctionCall]
        )
        return [struct_msg]