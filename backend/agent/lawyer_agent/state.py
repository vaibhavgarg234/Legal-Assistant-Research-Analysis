from typing import TypedDict, List, Any, Annotated
import operator
from langchain_core.messages import BaseMessage


class LawyerAgentState(TypedDict):
    query: str
    chat_history: List[BaseMessage]
    issues: List[str]  # Extracted legal issues
    facts: List[str]  # Extracted facts
    sub_queries: Annotated[List[str], operator.add]  # Sub-queries for retrieval
    retrieved_context: Annotated[List[str], operator.add]  # Retrieved documents/context
    answer_draft: str  # Draft answer
    answer_score: float  # Score from critic (0.0 to 1.0)
    iterations: Annotated[int, operator.add]  # Number of iterations
    final_analysis: str  # Final analysis
