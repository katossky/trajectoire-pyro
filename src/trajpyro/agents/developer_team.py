import os
import asyncio
import argparse

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
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
        create_and_switch_branch
    ],
)

coder = AssistantAgent(
    name = "coder",
    description = "the skilful coder",
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

tester = AssistantAgent(
    name = "tester",
    description = "the relentless tester",
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

team = SelectorGroupChat(
    participants=[manager, coder, tester],
    allow_repeated_speaker=True,
    model_client = get_client("moonshotai/kimi-k2:free"),
    selector_prompt = """Select an agent to perform next among :
    {roles}

    After reading the following conversation :
    {history}

    ... select an agent from {participants} to perform next.
    
    As a rule keep the manager writing unless they explicitly assign
    a task to a specific other agent.
    Then keep that agent speaking until they finish the
    task and write "DONE",
    At that moment give the way back to the manager.
    
    Always select one and only one agent.
    """,
    termination_condition = TextMentionTermination("TERMINATE") | MaxMessageTermination(100)
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