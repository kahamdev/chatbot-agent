"""The only tools the graph is allowed to run.

Add a tool by writing a read-only function and putting it in this list.
There is no dynamic import and no shell, SQL, or HTTP tool.
"""

from langchain_core.tools import BaseTool, tool

from chatbot_agent.tools.calculator import calculate
from chatbot_agent.tools.knowledge_search import search_knowledge


@tool
def calculator(expression: str) -> str:
    """Evaluate one arithmetic expression. Read-only. Use +, -, *, /, and parentheses."""
    return calculate(expression)


@tool
def knowledge_search(query: str) -> str:
    """Search the local notes shipped with this chatbot. Read-only reference data."""
    return search_knowledge(query)


def list_tools() -> list[BaseTool]:
    return [calculator, knowledge_search]


def allowed_tool_names() -> set[str]:
    return {item.name for item in list_tools()}
