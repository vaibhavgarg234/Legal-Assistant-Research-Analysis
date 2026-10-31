from ..state import LawyerAgentState


def finalizer(state: LawyerAgentState) -> dict:
    """Set the final analysis from the draft."""
    print("---FINALIZING ANALYSIS---")
    return {"final_analysis": state["answer_draft"]}
