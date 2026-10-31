from ..state import LawyerAgentState
from ..legacy_answer import generate_legacy_lawyer_answer


def drafter(state: LawyerAgentState) -> dict:
    """Generate draft answer using legacy logic."""
    print("---DRAFTING ANSWER---")
    query = state["query"]
    retrieved_context = "\n".join(state["retrieved_context"])

    answer_draft = generate_legacy_lawyer_answer(query, retrieved_context)

    return {"answer_draft": answer_draft}
