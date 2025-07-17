import os
import asyncio
import argparse

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TerminationCondition, TerminatedException
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.tools import TeamTool
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.tools.code_execution import PythonCodeExecutionTool
from autogen_agentchat.messages import StopMessage

class ConsecutiveEmptyTermination(TerminationCondition):
    """Stop after N blank messages in a row (default: 2)."""

    def __init__(self, n: int = 2):
        super().__init__()
        self._terminated = False
        self.n = n
        self._streak = 0                   # local counter
    
    @property
    def terminated(self) -> bool:
        return self._terminated

    async def reset(self) -> None:
        self._terminated = False

    async def __call__(self, events):            # events = the ‘delta’ since last check
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        for ev in events:
            txt = getattr(ev, "content", None)
            if not txt or str(txt).strip() == "":
                self._streak += 1
            else:
                self._streak = 0
        if self._streak >= self.n:         # rule satisfied → ask the team to stop
            self._streak = 0               # (optional) reset for next run
            return StopMessage(
                content=f"{self.n} consecutive empty messages",
                source="ConsecutiveEmptyTermination",
            )
        

from .utils import get_client, get_prompt

from .tools import (
    list_directories,
    list_files,
    read_file,
    create_directory,
    write_file,
    list_issues,
    get_issue_body,
    comment_issue,
    open_pull_request,
    delete_file,
    diff,
    commit_and_push_factory,
    insert_line,
    delete_line,
    create_and_switch_branch,
    run_tests,
    run_module
)

# advisor
# --> reviews everything
# --> advises architectural choices

# documentarian
# --> at the end, make sure everything is documented and add what's new to news.md

coder_base = AssistantAgent(
    name = "coder",
    description = "skilful coder",
    model_client = get_client(),
    model_client_stream=True,
    system_message = get_prompt("coder"),
    tools = [
        list_directories,
        list_files,
        read_file,
        insert_line,
        create_directory,
        write_file,
        delete_file,
        commit_and_push_factory("ai-coder"),
        run_module,
        PythonCodeExecutionTool(LocalCommandLineCodeExecutor()),
    ],
)

coder = RoundRobinGroupChat(
    [coder_base],
    termination_condition = TextMentionTermination("DONE") | MaxMessageTermination(50) | ConsecutiveEmptyTermination(n=2),
)

tester_base = AssistantAgent(
    name = "tester",
    description = "relentless tester",
    model_client = get_client(),
    model_client_stream=True,
    system_message = get_prompt("tester"),
    tools = [
        list_directories,
        list_files,
        read_file,
        create_directory,
        delete_file,
        write_file,
        insert_line,
        commit_and_push_factory("ai-tester"),
        run_tests,
        PythonCodeExecutionTool(LocalCommandLineCodeExecutor()),
    ],
)

tester = RoundRobinGroupChat(
    [tester_base],
    termination_condition = TextMentionTermination("DONE") | MaxMessageTermination(50) | ConsecutiveEmptyTermination(n=2),
)

manager = AssistantAgent(
    name = "manager",
    description = "the overall planner",
    model_client = get_client(),
    model_client_stream=True,
    system_message = get_prompt("manager"),
    tools = [
        list_directories,
        list_files,
        read_file,
        create_directory,
        write_file,
        insert_line,
        delete_line,
        list_issues,
        get_issue_body,
        comment_issue,
        open_pull_request,
        diff,
        commit_and_push_factory("ai-project-manager"),
        create_and_switch_branch,
        TeamTool(coder, "coder", "your team member for coding tasks"),
        TeamTool(tester, "tester", "your team member for testing tasks"),
    ],
)

devloper_team = RoundRobinGroupChat(
    [manager],
    termination_condition = TextMentionTermination("TERMINATE") | MaxMessageTermination(200) | ConsecutiveEmptyTermination(n=2),
)

# ------------------------------------------------------------
# Entry point – run once or looped in CI
# ------------------------------------------------------------

async def run(task):
    await Console(
        devloper_team.run_stream(task=task),
        output_stats=True
    )

def main():

    parser = argparse.ArgumentParser(
        prog="developer_team.py",
        description="Run the Developer Team agent",
    )

    parser.add_argument(
        "-t",
        "--task",
        metavar="TEXT",
        type=str,
        default="Pick a scheduled issue and solve it.",
        help="Specific task to give to the Owner agent",
    )
    
    args = parser.parse_args()

    asyncio.run(run(task = args.task))

if __name__ == "__main__":

    main()