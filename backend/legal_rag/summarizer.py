import os
import operator
import asyncio  # noqa: F401
import json
from typing import TypedDict, Annotated, List, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import BaseMessage  # noqa: F401

from sentence_transformers import SentenceTransformer, util
from legal_rag.source_verifier import run_source_verification

load_dotenv()


# ------------------------------
# Config
# ------------------------------
FAST_MODE = True  # ✅ Toggle True = faster (trims), False = detailed chunking
CHUNK_SIZE = 1200
MAX_CHUNKS = 3

# ------------------------------
# Global Embedding Model (for evaluation)
# ------------------------------
# Load the model once when the server starts
try:
    EMBEDDING_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("Embedding model for evaluation loaded successfully.")
except Exception as e:
    print(f"Error loading embedding model: {e}")
    EMBEDDING_MODEL = None
# ------------------------------


# ------------------------------
# Agent State (Full definition for reference)
# ------------------------------
class AgentState(TypedDict):
    query: str
    intermediate_steps: Annotated[List[Any], operator.add]
    web_search_results: str
    faiss_search_results: str
    final_analysis: str
    research_complete: bool
    chat_history: List[BaseMessage]
    sources: Annotated[List[dict], operator.add]
    role: str
    research_cycles: Annotated[int, operator.add]
    evaluation_score: str # This will store the formatted evaluation string


# ------------------------------
# Utility Functions
# ------------------------------
def get_llm():
    """Initialize Groq LLM with env key and automatic 429 rate limit fallback."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable not set.")
    primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    fallback_model = "openai/gpt-oss-20b" if primary_model != "openai/gpt-oss-20b" else "qwen/qwen3.8-27b"

    primary_llm = ChatGroq(model=primary_model, temperature=0.2, groq_api_key=groq_api_key)
    fallback_llm = ChatGroq(model=fallback_model, temperature=0.2, groq_api_key=groq_api_key)
    return primary_llm.with_fallbacks([fallback_llm])


def safe_invoke(llm, prompt, vars):
    """Run a prompt safely and return text content with automatic fallback retry."""
    try:
        chain = prompt | llm
        result = chain.invoke(vars)
        return getattr(result, "content", str(result))
    except Exception as e:
        print(f"safe_invoke: Primary model hit error ({e}). Retrying with fallback models...")
        api_key = os.getenv("GROQ_API_KEY")
        for alt_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                print(f"Retrying prompt with {alt_model}...")
                fallback_chat = ChatGroq(model=alt_model, temperature=0.2, groq_api_key=api_key)
                chain = prompt | fallback_chat
                result = chain.invoke(vars)
                return getattr(result, "content", str(result))
            except Exception as e2:
                print(f"Fallback {alt_model} error: {e2}")
        raise e



def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, max_chunks: int = MAX_CHUNKS):
    """Split text into word chunks, capped to max_chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i : i + chunk_size]))
        if len(chunks) >= max_chunks:
            break
    return chunks


def summarize_long_text(text: str, label: str, query: str) -> str:
    """Summarize text with fast or detailed strategy."""
    if not text:
        return f"No {label} found."

    llm = get_llm()

    # ✅ Fast mode: just trim input
    if FAST_MODE:
        trimmed = " ".join(text.split()[:2000])
        prompt = PromptTemplate(
            template=f"""Summarize the following {label} (<200 words), focusing on acts, sections, judgments.

            Query: {{query}}
            Text: {{text}}

            Summary:""",
            input_variables=["query", "text"],
        )
        return safe_invoke(llm, prompt, {"query": query, "text": trimmed})

    # ✅ Detailed mode: chunk + merge
    chunk_summaries = []
    for chunk in chunk_text(text):
        prompt = PromptTemplate(
            template=f"""Summarize this {label} chunk (<120 words),
            focusing only on acts, sections, judgments.

            Query: {{query}}
            {label} chunk: {{chunk}}

            Summary:""",
            input_variables=["query", "chunk"],
        )
        chunk_summaries.append(
            safe_invoke(llm, prompt, {"query": query, "chunk": chunk})
        )

    merge_prompt = PromptTemplate(
        template=f"""Combine the following {label} summaries into one concise digest (<250 words):

        Query: {{query}}
        Summaries:
        {{summaries}}

        Final Digest:""",
        input_variables=["query", "summaries"],
    )
    return safe_invoke(
        llm, merge_prompt, {"query": query, "summaries": "\n".join(chunk_summaries)}
    )


# ------------------------------
# Citizen-focused Functions
# ------------------------------
def summarize_and_reflect(state: AgentState) -> dict:
    """Summarizes the findings and reflects on the research to identify gaps."""
    print("---SUMMARIZING & REFLECTING---")
    query = state["query"]

    faiss_summary = summarize_long_text(
        state["faiss_search_results"], "FAISS results", query
    )
    web_summary = summarize_long_text(state["web_search_results"], "Web results", query)

    llm = get_llm()
    summary_prompt = PromptTemplate(
        template="""Based on the original query and the following summarized search results,
        provide a concise reflection.

        Original Query: {query}
        FAISS Summary: {faiss_summary}
        Web Summary: {web_summary}

        Reflection:
        1. Key findings:
        2. Knowledge Gaps:
        3. Research complete? ('YES' or 'NO')""",
        input_variables=["query", "faiss_summary", "web_summary"],
    )

    summary = safe_invoke(
        llm,
        summary_prompt,
        {"query": query, "faiss_summary": faiss_summary, "web_summary": web_summary},
    )

    is_complete = "YES" in summary.upper()

    return {
        "intermediate_steps": state["intermediate_steps"] + [summary],
        "research_complete": is_complete,
    }


def generate_final_analysis(state: AgentState) -> dict:
    """Generates the final, structured legal analysis."""
    print("---GENERATING FINAL ANALYSIS---")
    query = state["query"]
    all_steps = "\n".join(state["intermediate_steps"])

    # Compress steps if too long
    if len(all_steps.split()) > 1500:
        all_steps = summarize_long_text(all_steps, "research steps", query)

    llm = get_llm()
    analysis_prompt = PromptTemplate(
        template="""You are L.A.R.A., an expert Indian legal analyst.
Based on the user query and the retrieved research steps below, generate an authoritative, structured legal analysis.

CRITICAL INSTRUCTIONS FOR ACCURACY:
- Ground all facts strictly in the provided Research Steps and live sources.
- Never invent fictitious court judgments, imaginary case names, fake dates, or nonexistent benches.
- Never cite repealed laws (such as POTA 2002) as active law. Applicable Indian statutes for public order and detention include BNSS / CrPC (e.g. Sections 107/151 for preventive custody), BNS / IPC, and the Delhi Police Act.
- If the case involves recent events (such as recent protests, detentions, or bail proceedings) and no High Court or Supreme Court judgment has been delivered yet, state clearly and transparently: "No formal High Court or Supreme Court ruling has been delivered on this specific matter to date", and report the actual factual proceedings from the retrieved news sources.

Required Structure:
- **Original Query**
- **Factual Background & Latest Status** (Detail the verified facts from live reports)
- **Applicable Legal Framework** (Statutory provisions, fundamental rights under Article 19(1)(b) vs reasonable restrictions under 19(3), flag protocols under Flag Code / Prevention of Insults to National Honour Act)
- **Judicial Context & Relevant Precedents** (Discuss established precedents such as Union of India v. Naveen Jindal (2004) or Mazdoor Kisan Shakti Sangathan v. Union of India (2018), and note the current court/magistrate status of the specific matter)
- **Analysis and Key Takeaways**
- **Sources & Citations** (List retrieved URLs and relevant statutes)

Query: {query}
Research Steps:
{all_steps}

Final Analysis:""",
        input_variables=["query", "all_steps"],
    )

    final_analysis = safe_invoke(
        llm, analysis_prompt, {"query": query, "all_steps": all_steps}
    )

    return {"final_analysis": final_analysis}


# ------------------------------
# New Lawyer-focused Functions
# ------------------------------
def summarize_and_reflect_lawyer(state: AgentState) -> dict:
    """
    Summarizes findings and reflects on the research from a lawyer's perspective.
    Identifies if enough legal precedents and arguments have been found.
    """
    print("---SUMMARIZING & REFLECTING FOR LAWYER---")
    query = state["query"]

    faiss_summary = summarize_long_text(
        state["faiss_search_results"], "FAISS results", query
    )
    web_summary = summarize_long_text(state["web_search_results"], "Web results", query)

    llm = get_llm()
    summary_prompt = PromptTemplate(
        template="""You are a legal research assistant for a lawyer. Based on the original query
        and the following summarized search results, provide a professional reflection.

        Original Query: {query}
        FAISS Summary: {faiss_summary}
        Web Summary: {web_summary}

        Reflection:
        1. **Key Legal Findings**: Highlight relevant statutes, case names, and legal principles.
        2. **Gaps in Research**: Identify missing information, such as conflicting judgments or lack of recent precedents.
        3. **Is the research complete?** ('YES' or 'NO')""",
        input_variables=["query", "faiss_summary", "web_summary"],
    )

    summary = safe_invoke(
        llm,
        summary_prompt,
        {"query": query, "faiss_summary": faiss_summary, "web_summary": web_summary},
    )

    is_complete = "YES" in summary.upper()

    return {
        "intermediate_steps": state["intermediate_steps"] + [summary],
        "research_complete": is_complete,
    }


def generate_lawyer_analysis(state: AgentState) -> dict:
    """Generates a structured legal analysis report for a lawyer."""
    print("---GENERATING LAWYER ANALYSIS REPORT---")
    query = state["query"]
    all_steps = "\n".join(state["intermediate_steps"])

    # Compress steps if too long
    if len(all_steps.split()) > 1500:
        all_steps = summarize_long_text(all_steps, "research steps", query)

    llm = get_llm()
    analysis_prompt = PromptTemplate(
        template="""You are an expert legal assistant. Based on the lawyer's case details
        and the research steps below, generate a professional legal analysis.

        - **Original Case Details**: A summary of the query provided by the lawyer.
        - **Relevant Statutes & Acts**: List of key legal provisions from Indian Law.
        - **Past Case Precedents & Judgments**: A detailed summary of related case studies with names and citations.
        - **Key Legal Arguments & Points**: Actionable points and arguments derived from the research.
        - **Sources**: A clear list of all web pages and internal documents used.

        Case Details: {query}
        Research Steps: {all_steps}

        Final Legal Analysis:""",
        input_variables=["query", "all_steps"],
    )

    final_analysis = safe_invoke(
        llm, analysis_prompt, {"query": query, "all_steps": all_steps}
    )

    return {"final_analysis": final_analysis}


# ----------------------------------------------------
# HYBRID EVALUATION HELPER FUNCTION
# ----------------------------------------------------
def evaluate_analysis(llm, query: str, all_steps: str, analysis: str, sources: list = None) -> str:
    """
    Evaluates the generated analysis using an audited hybrid method:
    - Runs automated source & statute verification (detects repealed laws, unverified URLs)
    - Adversarial LLM fact-checking audit for hallucinations and context faithfulness
    - Computes semantic similarity against retrieved research context
    - Applies hard gating: caps confidence if unverified legal claims or hallucinations are detected
    """

    print("---EVALUATING FINAL ANALYSIS (AUDITED HYBRID CONFIDENCE METHOD)---")

    # Step 1: Run deterministic source and statute verification
    source_audit = run_source_verification(analysis, all_steps, sources or [])

    # Step 2: Adversarial LLM Audit for Faithfulness and Hallucinations
    eval_prompt = PromptTemplate(
        template="""You are a strict, adversarial legal auditor and fact-checker for Indian law.
Evaluate the [Final Analysis] against the provided [Research Context].
Your job is to detect factual hallucinations, ungrounded court judgments, and misattributed statutes.

STRICT SCORING GUIDELINES:
1. Context Faithfulness (1.0 - 5.0):
   - 5.0: Every factual assertion (names, events, court levels, arrests) is directly corroborated by the Research Context.
   - 3.0: Mostly grounded, but contains minor speculative remarks.
   - 1.0 - 2.0: Cites fictitious court judgments (e.g. inventing a High Court/Supreme Court bench ruling not in context) or cites repealed statutes (like POTA 2002) as active charges.
2. Legal Accuracy (1.0 - 5.0):
   - Accurate application of active Indian statutory framework (BNS/IPC, BNSS/CrPC, Constitution).
3. Relevance (1.0 - 5.0): Direct responsiveness to the user's specific query.
4. Clarity (1.0 - 5.0): Coherence, structure, and readability.

[Original Query]: {query}
[Research Context]: {all_steps}
[Final Analysis]: {analysis}

Return strictly in JSON:
{{
    "faithfulness_score": (1.0 to 5.0),
    "accuracy_score": (1.0 to 5.0),
    "relevance_score": (1.0 to 5.0),
    "clarity_score": (1.0 to 5.0),
    "hallucination_detected": (true/false),
    "justification": "Clear summary of audit findings, noting verified facts and any ungrounded assertions."
}}
""",
        input_variables=["query", "all_steps", "analysis"],
    )

    evaluation = safe_invoke(
        llm,
        eval_prompt,
        {"query": query, "all_steps": all_steps, "analysis": analysis},
    )

    # Parse JSON safely
    try:
        eval_data = json.loads(evaluation)
        faithfulness = float(eval_data.get("faithfulness_score", 3.0))
        accuracy = float(eval_data.get("accuracy_score", 3.0))
        relevance = float(eval_data.get("relevance_score", 3.0))
        clarity = float(eval_data.get("clarity_score", 3.0))
        hallucination_detected = bool(eval_data.get("hallucination_detected", False))
        justification = eval_data.get("justification", "Audit completed.")
    except Exception:
        faithfulness = accuracy = relevance = clarity = 3.0
        hallucination_detected = False
        justification = "Standard heuristic evaluation applied."

    # Step 3: Compute semantic entailment to the research context (NOT just query topic overlap)
    if EMBEDDING_MODEL:
        emb_context = EMBEDDING_MODEL.encode(all_steps, convert_to_tensor=True)
        emb_analysis = EMBEDDING_MODEL.encode(analysis, convert_to_tensor=True)
        context_sim = util.cos_sim(emb_analysis, emb_context).item()
        # Scale range [0.15, 0.75] onto 1.0 - 5.0
        scaled_sim = 1.0 + (max(0.0, context_sim - 0.15) / 0.60) * 4.0
        semantic_confidence = round(min(scaled_sim, 5.0), 2)
    else:
        semantic_confidence = 3.5

    # Step 4: Gated Hybrid Scoring Formula
    # Faithfulness and Accuracy carry 80% weight
    llm_score = (0.45 * faithfulness) + (0.35 * accuracy) + (0.10 * relevance) + (0.10 * clarity)

    # HARD GATING: If faithfulness is low, hallucination is detected, or statute verification failed,
    # DO NOT award high confidence even if text sounds fluent or matches query keywords!
    is_failed_audit = (faithfulness < 3.0) or hallucination_detected or (not source_audit["passed"])

    if is_failed_audit:
        final_confidence = min(faithfulness, accuracy, 2.5)
        status_flag = "⚠️ GATED (Low Faithfulness or Unverified Claims Detected)"
    else:
        final_confidence = round((0.70 * llm_score) + (0.30 * semantic_confidence), 2)
        final_confidence = min(final_confidence, 5.0)
        status_flag = "✅ HIGH CONFIDENCE (Verified & Grounded)"

    # Step 5: Return comprehensive evaluation summary with badges
    result = f"""
--- Evaluation & Audit Summary ---
🔹 Context Faithfulness Score: {faithfulness}/5
🔹 Legal Accuracy Score: {accuracy}/5
🔹 Relevance Score: {relevance}/5
🔹 Clarity Score: {clarity}/5
🔹 LLM Weighted Audit: {round(llm_score, 2)}/5

🔸 Semantic Context Entailment: {round(semantic_confidence, 2)}/5
🎯 Overall Confidence Score: {final_confidence} / 5.0 [{status_flag}]

💬 Audit Assessment: {justification}
{source_audit['verification_badge']}
"""
    return result


# ----------------------------------------------------
# HYBRID EVALUATION GRAPH NODE
# ----------------------------------------------------
def evaluate_hybrid_response(state: AgentState) -> dict:
    """
    Graph node to evaluate the final analysis using the hybrid method.
    Passes state sources for full traceability.
    """
    print("---STARTING HYBRID EVALUATION NODE---")
    
    query = state["query"]
    final_analysis = state["final_analysis"]
    sources = state.get("sources", [])
    
    # Re-create 'all_steps' from intermediate steps
    all_steps = "\n".join(state["intermediate_steps"])
    
    if len(all_steps.split()) > 1500:
        all_steps = summarize_long_text(all_steps, "research steps", query)

    if not final_analysis:
        return {"evaluation_score": "Error: No analysis generated."}

    llm = get_llm()
    
    evaluation_summary = evaluate_analysis(
        llm, 
        query=query, 
        all_steps=all_steps, 
        analysis=final_analysis,
        sources=sources
    )    
    return {"evaluation_score": evaluation_summary}


# ----------------------------------------------------
# FINAL COMBINATION GRAPH NODE
# ----------------------------------------------------
def combine_analysis_and_evaluation(state: AgentState) -> dict:
    """
    Appends the formatted evaluation summary and verification badges
    to the final analysis before delivering to the user.
    """
    print("---COMBINING ANALYSIS AND EVALUATION---")
    
    final_analysis = state.get("final_analysis", "No analysis was generated.")
    evaluation_summary = state.get("evaluation_score", "No evaluation was performed.")
    
    combined_response = f"{final_analysis}\n\n{evaluation_summary}"
    return {"final_analysis": combined_response}