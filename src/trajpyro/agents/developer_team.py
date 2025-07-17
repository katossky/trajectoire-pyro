import os
import asyncio
import argparse

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.tools import TeamTool
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.tools.code_execution import PythonCodeExecutionTool

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
    commit_and_push,
    insert_line,
    delete_line,
    create_and_switch_branch,
)

# advisor
# --> reviews everything
# --> advises architectural choices

# documentarian
# --> at the end, make sure everything is documented and add what's new to news.md

coder_base = AssistantAgent(
    name = "coder_base",
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
        commit_and_push,
        PythonCodeExecutionTool(LocalCommandLineCodeExecutor(work_dir="coding")),
    ],
)

coder = RoundRobinGroupChat(
    [coder_base],
    termination_condition = TextMentionTermination("DONE") | MaxMessageTermination(50),
)

tester_base = AssistantAgent(
    name = "tester_base",
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
        commit_and_push,
        PythonCodeExecutionTool(LocalCommandLineCodeExecutor(work_dir="coding")),
    ],
)

tester = RoundRobinGroupChat(
    [tester_base],
    termination_condition = TextMentionTermination("DONE") | MaxMessageTermination(50),
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
        commit_and_push,
        create_and_switch_branch,
        TeamTool(coder, "coder", "your team member for coding tasks"),
        TeamTool(tester, "tester", "your team member for testing tasks"),
    ],
)

devloper_team = RoundRobinGroupChat(
    [manager],
    termination_condition = TextMentionTermination("TERMINATE") | MaxMessageTermination(100),
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