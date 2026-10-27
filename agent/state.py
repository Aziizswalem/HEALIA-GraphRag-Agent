from operator import add
from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # AG-UI / CopilotKit conversation thread (LangChain BaseMessage list)
    messages: Annotated[list, add_messages]
    question: str
    schema_context: str
    cypher_draft: str
    validation_error: Optional[str]
    graph_results: Optional[list]
    retry_count: int
    final_answer: str
    trace_id: str
    # Appended by each node (LangGraph reducer)
    trace_steps: Annotated[list[dict], add]
    session_id: Optional[str]
    genui_blocks: Optional[list[dict]]

