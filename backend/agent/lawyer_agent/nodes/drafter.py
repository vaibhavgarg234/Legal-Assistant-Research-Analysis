from ..state import LawyerAgentState
from ..legacy_answer import generate_legacy_lawyer_answer
from legal_rag.query_rewriter import format_chat_history


def drafter(state: LawyerAgentState) -> dict:
    """Generate draft answer using legacy logic with conversational continuity."""
    print("---DRAFTING ANSWER---")
    query = state["query"]
    retrieved_context = "\n".join(state["retrieved_context"])
    chat_history = state.get("chat_history", [])
    history_str = format_chat_history(chat_history)

    answer_draft = generate_legacy_lawyer_answer(query, retrieved_context, chat_history=history_str)

    return {"answer_draft": answer_draft}
