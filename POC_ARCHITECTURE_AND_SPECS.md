# L.A.R.A. (Legal Analysis & Research Assistant)
## Complete Proof of Concept (POC) Architecture, System Design & Technical Specification

---

## 1. Executive Summary & Purpose

**L.A.R.A.** is an agentic, retrieval-augmented legal research assistant tailored for Indian law. It operates across two primary user personas:
1. **Common Citizen Agent**: Translates complex legalese into clear, structured, actionable explanations with statutory citations, practical steps, and hybrid confidence scores.
2. **Lawyer Agent**: Performs deep iterative legal research, issue extraction, multi-angle sub-query planning, adversarial critique, and structured precedent analysis.

This document serves as the **definitive Proof of Concept (POC) & System Architecture Specification**. It details:
- How the system is architected across LangGraph, LangChain, FAISS, Tavily, and Groq LLMs.
- The root cause analysis of recent failures (e.g., hallucinations on recent events like the *Saurav Das & Ashutosh Ranka Jantar Mantar* case, empty web search context, and HTTP 429 rate limit exceptions).
- The exact target data flows, state definitions, prompts, and anti-hallucination guardrails required for production-grade reliability.

---

## 2. High-Level Architecture & Technology Stack

```
+-----------------------------------------------------------------------------------+
|                                 USER INTERFACES                                   |
|   1. Streamlit Interactive App (:8501)       2. React + Vite Modern UI (:5173)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         API & ROUTING LAYER (FastAPI :8000)                       |
|   - Endpoint: POST /query (role, user_query, thread_id)                           |
|   - Router (`agent/router.py`): Case-insensitive dispatch to Citizen or Lawyer   |
|   - SQLite Persistence (`db.py`): Session threads & conversational history        |
+-----------------------------------------------------------------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
+----------------------------------------+   +--------------------------------------+
|       CITIZEN AGENT (LangGraph)        |   |        LAWYER AGENT (LangGraph)      |
|  1. Query Rewriter                     |   |  1. Issue & Fact Extractor           |
|  2. Parallel Retrieval (FAISS + Web)   |   |  2. Sub-Query Planner                |
|  3. Summarize & Reflect (Cycle Loop)   |   |  3. Multi-Query Parallel Retriever   |
|  4. Final Analysis Generator           |   |  4. Legal Draft Answer Generator     |
|  5. Hybrid Confidence Evaluator        |   |  5. Adversarial Critic & Score Loop  |
|  6. Combined Synthesis Node            |   |  6. Final Verified Precedent Output  |
+----------------------------------------+   +--------------------------------------+
                     \                                       /
                      +------------------+------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                              DUAL RETRIEVAL ENGINE                                |
|  - Static Legal DB: FAISS Index (4,209 vectors, HuggingFace sentence embeddings)  |
|  - Dynamic Live Web: Tavily Web Search API (News, recent arrests, high court ord.) |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         INFERENCE & MODEL ORCHESTRATION                           |
|  - Groq Cloud API: Low-latency open-weights LLMs                                  |
|  - Cascade Failover: `qwen/qwen3.8-27b` (Primary) -> `openai/gpt-oss-20b` (Backup)|
+-----------------------------------------------------------------------------------+
```

### Technology Stack Details:
- **Orchestration**: `langgraph` (StateGraph, conditional loops, checkpointing), `langchain` (LCEL runnables, prompt templates).
- **Embeddings & Vector Store**: `sentence-transformers/all-MiniLM-L6-v2` & `paraphrase-MiniLM-L3-v2` with `faiss-cpu`.
- **Live Search**: `langchain-tavily` (`TavilySearch` API wrapper).
- **LLM Inference**: `langchain-groq` (`ChatGroq`) with automated exception-handling fallbacks.
- **Backends**: FastAPI (REST endpoints) + Streamlit (Rapid prototyping UI).
- **Frontend**: React 18, Vite, Lucide Icons, Tailwind-compatible styling.

---

## 3. Deep-Dive Root Cause Analysis: Why Hallucinations & Failures Occurred

### Problem Case Study:
**User Query**: *"What happened in Saurav Das Ashutosh Ranka detention case for Jantar Mantar flag hoisting issue?"*

**Erroneous Output Produced**:
- Stated that the activists were charged under the **Prevention of Terrorism Act (POTA)**. *(POTA was repealed in 2004—factually impossible in 2024/2026).*
- Invented fictitious judgments: *"Delhi High Court (April 2024) quashed the arrest"* and *"Supreme Court of India (June 2024) upheld the decision"*.

### Root Cause 1: Tavily Dictionary Parsing Bug (The Critical Starvation Flaw)
In `backend/legal_rag/retrieval.py` and `backend/agent/lawyer_agent/nodes/retriever.py`:
```python
# BUGGY CODE:
web_search_tool = TavilySearch(max_results=5, tavily_api_key=tavily_api_key)
web_results = web_search_tool.invoke(query)  # <-- Returns a Python dict: {'query': ..., 'results': [...]}

web_content = ""
for result in web_results:                   # <-- BUG: Iterates over DICTIONARY KEYS!
    web_content += result + "\n\n"
```
- **Consequence**: Python iterated over the dictionary keys (`"query"`, `"follow_up_questions"`, `"answer"`, `"images"`, `"results"`, `"response_time"`, `"request_id"`).
- `web_content` became literally:
  ```
  query\n\nfollow_up_questions\n\nanswer\n\nimages\n\nresults\n\nresponse_time\n\nrequest_id\n\n
  ```
- **Every single piece of live web text, article titles, snippets, and URLs were completely discarded!**

### Root Cause 2: Static FAISS Database Blind Spot
- The FAISS database is a static collection of statutory provisions and classic case law (e.g., CrPC, Constitution, IBC, SEBI).
- When a query asks about a contemporary event (such as the October 2026 preventive detention of Cockroach Janta Party activists at Jantar Mantar), FAISS returns similarity matches for generic arrest warrants (e.g., Section 70 CrPC) with no knowledge of the specific incident.
- Combined with Root Cause 1, the LLM received **0 factual context about the real incident**.

### Root Cause 3: Rigid Template Pressure
- The generation prompt strictly mandated:
  ```
  - **Legal Context**
  - **Case Law Summary**
  ```
- Because the LLM was forced to supply a "Case Law Summary" for a specific case with zero factual context, it fabricated courts, dates, and repealed statutes (POTA) to satisfy the schema.

### Root Cause 4: Token Exhaustion (HTTP 429)
- Running 3 repetitive research cycles with an unbudgeted 120B model consumed 199,879 tokens against Groq's free-tier limit of 200,000 tokens/day (TPD), locking the model until daily reset.

---

## 4. How Each Component Must Work (Target Specification)

### 4.1 Component 1: Query Routing & Intent Classification (`agent/router.py`)
- **Responsibility**: Receive user input, inspect role selection (`"Common Citizen"` vs `"Lawyer"`), fetch conversation history from SQLite, and invoke the appropriate LangGraph compiled app.
- **Requirement**: Normalizes roles case-insensitively (`role.strip().lower()`), sets `recursion_limit: 50`, and passes thread identifiers for persistence.

### 4.2 Component 2: Intelligent Query Rewriting (`legal_rag/query_rewriter.py`)
- **Responsibility**: Deconstruct the user query into optimized search terms.
- **Requirement**:
  - Distinguish between **Statutory/Precedent Queries** (for FAISS) and **Factual/Current Event Queries** (for Tavily Live Search).
  - Return clean JSON containing targeted search queries without commentary.

### 4.3 Component 3: Dual-Channel Retrieval Engine (`legal_rag/retrieval.py` & `retriever.py`)
- **FAISS Retrieval**:
  - Queries local index with `k=5`.
  - Attaches source metadata (`source`, `statute`, `section`).
- **Live Web Retrieval (Robust Parser)**:
  - Must extract `item['title']`, `item['url']`, and `item['content']` from `web_results.get('results', [])`.
  - Formats rich snippets with publication dates where available.
  - Returns structured source objects for frontend rendering.

### 4.4 Component 4: Summarization & Reflection Loop (`legal_rag/summarizer.py`)
- **Responsibility**: Compress raw search findings into concise legal points and identify knowledge gaps.
- **Reflection Criteria**:
  - Determines if the query requires modern factual verification vs theoretical statutory interpretation.
  - If web results provide clear facts, flags `research_complete = True` to terminate early without burning cycles or API tokens.
  - Limits max cycles to 3 as a hard guardrail.

### 4.5 Component 5: Grounded Final Analysis Generator (`legal_rag/summarizer.py`)
- **Anti-Hallucination Directive**:
  - Strict grounding: The LLM must categorize findings into:
    1. **Verified Real-World Facts** (from Web Search).
    2. **Applicable Statutory Framework** (from FAISS/Indian Penal/Procedure Code).
    3. **Judicial Status**: Explicitly state if no High Court or Supreme Court ruling exists yet, rather than inventing one.
  - Explicit prohibition against citing repealed laws unless discussing historical context.

### 4.6 Component 6: Hybrid Confidence Evaluation Node (`evaluate_hybrid_response`)
- **Responsibility**: Score the generated analysis before presenting it to the user.
- **Formulation**:
  $$\text{LLM Score} = 0.4 \times \text{Relevance} + 0.4 \times \text{Faithfulness} + 0.2 \times \text{Clarity}$$
  $$\text{Semantic Similarity} = \text{CosineSim}(\text{Analysis}, \text{Query}) + \text{CosineSim}(\text{Analysis}, \text{Context})$$
  $$\text{Final Confidence} = 0.6 \times \text{LLM Score} + 0.4 \times \text{Semantic Score} \quad (\text{Scale } 1.0 - 5.0)$$

---

## 5. Detailed Component Data Flow (LangGraph State Machine)

```mermaid
graph TD
    Start([User Enters Query]) --> Router{Router: Role?}
    
    %% Citizen Path
    Router -->|Citizen| Rewrite[rewrite_query: Formulate Legal & Fact Queries]
    Rewrite --> Research[perform_research: Parallel FAISS + Tavily Web]
    Research --> Summarize[summarize_and_reflect: Extract Facts & Gaps]
    Summarize --> Incr[increment_counter: Cycle Count + 1]
    Incr --> Check{Complete or Max Cycles?}
    Check -->|No| Research
    Check -->|Yes| FinalGen[generate_final_analysis: Grounded Synthesis]
    FinalGen --> Eval[evaluate_hybrid_response: LLM + Cosine Confidence]
    Eval --> Combine[combine_analysis_and_evaluation: Append Score & Sources]
    Combine --> EndCitizen([Deliver to Streamlit / React UI])

    %% Lawyer Path
    Router -->|Lawyer| Extr[issue_extractor: Extract Issues & Facts]
    Extr --> Plan[planner: Break into 3-5 Sub-Queries]
    Plan --> LawRet[retriever: Multi-Query Search across FAISS & Web]
    LawRet --> Draft[draft_answer: In-Depth Legal Memo]
    Draft --> Critic[critic: Adversarial Evaluation & Grading]
    Critic --> CritCheck{Score >= 0.8 or Iterations >= 3?}
    CritCheck -->|No| Plan
    CritCheck -->|Yes| EndLawyer([Deliver Professional Legal Memo])
```

---

## 6. Target Code Implementations for Fixes

### 6.1 Fixed Web Search & Parser (`backend/legal_rag/retrieval.py`)

```python
import os
from pathlib import Path
from typing import TypedDict, Annotated, List, Any
import operator
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_tavily import TavilySearch

backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

def extract_web_content(raw_results):
    """
    Robustly handles dictionary, list, or string outputs from TavilySearch
    and formats comprehensive snippets with URLs and titles.
    """
    content_pieces = []
    sources = []

    if isinstance(raw_results, dict):
        results_list = raw_results.get("results", [])
    elif isinstance(raw_results, list):
        results_list = raw_results
    elif isinstance(raw_results, str):
        return raw_results, [{"type": "web", "content": raw_results}]
    else:
        results_list = []

    for item in results_list:
        if isinstance(item, dict):
            title = item.get("title", "Web Source")
            url = item.get("url", "")
            snippet = item.get("content", "") or item.get("snippet", "")
            if snippet:
                formatted = f"**Source**: [{title}]({url})\n**Summary**: {snippet.strip()}"
                content_pieces.append(formatted)
                sources.append({"type": "web", "title": title, "url": url, "content": snippet})
        elif isinstance(item, str) and item.strip():
            content_pieces.append(item.strip())
            sources.append({"type": "web", "content": item})

    combined_text = "\n\n---\n\n".join(content_pieces) if content_pieces else "No web results retrieved."
    return combined_text, sources


def perform_research(state: dict) -> dict:
    """Executes parallel legal database search and live web search."""
    print("---PERFORMING RESEARCH---")
    query = state.get("rewritten_query") or state["query"]
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    # 1. FAISS Search
    faiss_docs = legal_database_search.invoke(query)
    faiss_content = ""
    sources = []
    for doc in faiss_docs:
        faiss_content += doc.page_content + "\n\n"
        if doc.metadata:
            sources.append({"type": "document", "metadata": doc.metadata})

    # 2. Live Web Search (with correct extraction)
    web_content = "No web search executed."
    if tavily_api_key:
        try:
            web_search_tool = TavilySearch(max_results=6, tavily_api_key=tavily_api_key)
            raw_web_results = web_search_tool.invoke(query)
            web_content, web_sources = extract_web_content(raw_web_results)
            sources.extend(web_sources)
        except Exception as e:
            web_content = f"Web search error: {e}"

    print(f"---RESEARCH COMPLETE (Retrieved {len(faiss_docs)} FAISS docs, {len(sources)} sources)---")

    return {
        "faiss_search_results": faiss_content,
        "web_search_results": web_content,
        "sources": sources,
        "intermediate_steps": [
            f"FAISS Retrieval Context:\n{faiss_content[:1500]}",
            f"Live Web Context:\n{web_content[:2500]}",
        ],
    }
```

### 6.2 Grounded, Anti-Hallucination Prompt (`backend/legal_rag/summarizer.py`)

```python
analysis_prompt = PromptTemplate(
    template="""You are L.A.R.A, an authoritative and rigorous Indian legal analyst.
Your mandate is to provide factual, verified legal analysis strictly grounded in Indian Law and the retrieved context.

[STRICT FACTUAL INTEGRITY INSTRUCTIONS]
1. GROUNDING MANDATE: Rely exclusively on verifiable facts from the Research Context. 
2. DO NOT FABRICATE: Never invent court judgments, imaginary benches, fake hearing dates, or fictitious case citations.
3. REPEALED LAWS: Do NOT cite repealed laws (such as POTA 2002) as active law. Active security and public order laws include the Bharatiya Nyaya Sanhita (BNS) / IPC, BNSS / CrPC (e.g., Section 107/151 for preventive detention), and Delhi Police Act.
4. CONTEMPORARY PROTESTS & ARRESTS: If the query concerns recent events (e.g., detentions at Jantar Mantar), state clearly what actually occurred according to the news sources (e.g., preventive detention under Special Executive Magistrate, violation of protest restrictions, Tihar Jail custody, bail status). If no High Court or Supreme Court ruling has been delivered, state explicitly: "No formal High Court or Supreme Court judgment has been delivered on this specific incident to date."

Original Query: {query}

Research Context:
{all_steps}

Generate your response in the following structured format:
### 1. Executive Summary & Factual Background
(Detail what actually occurred based on retrieved live reports)

### 2. Legal Framework & Applicable Indian Statutes
(Detail governing sections: e.g., Right to Protest under Article 19(1)(b) vs reasonable restrictions under 19(3); Emblems and Names Act / Prevention of Insults to National Honour Act, 1971; Preventive custody provisions under CrPC / BNSS)

### 3. Judicial Status & Case Precedents
(Detail relevant precedents on flag hoisting e.g. Union of India v. Naveen Jindal (2004) and Mazdoor Kisan Shakti Sangathan v. Union of India (2018) on Jantar Mantar protests. Explicitly note the absence of fictitious rulings)

### 4. Practical Implications & Legal Assessment
(Objective analysis of rights, procedural safeguards, and recommendations)

### 5. Authoritative Sources & Citations
(List actual retrieved URLs and statutory sections)
""",
    input_variables=["query", "all_steps"],
)
```

---

## 7. Model Allocation & Quota Management

To avoid HTTP 429 interruptions while preserving deep reasoning quality:

| Role / Function | Configured Primary Model | Automatic Fallback Model | Why Selected |
|---|---|---|---|
| **Query Rewriter** | `qwen/qwen3.8-27b` | `openai/gpt-oss-20b` | Fast entity extraction without token burn |
| **Research Summarizer** | `qwen/qwen3.8-27b` | `openai/gpt-oss-20b` | Accurate multi-paragraph synthesis |
| **Final Legal Analysis** | `qwen/qwen3.8-27b` | `openai/gpt-oss-20b` | High legal reasoning benchmark, distinct quota |
| **Hybrid Evaluator** | `qwen/qwen3.8-27b` | `openai/gpt-oss-20b` | Strict numeric JSON calibration |

*Note on 120B Model*: `openai/gpt-oss-120b` can be re-enabled in `.env` (`GROQ_MODEL=openai/gpt-oss-120b`) when high daily token allowances are available. The automatic failover catches 429 errors and routes to `qwen/qwen3.8-27b` seamlessly.

---

## 8. Implementation Checklist & Verification Matrix

- [x] **1. Audit existing codebase**
  - **Root Cause 1 (Web Search Starvation)**: `TavilySearch.invoke(query)` returns a dictionary `{'results': [...]}`. Iterating `for result in web_results` traversed only dictionary keys (`'query'`, `'follow_up_questions'`, `'results'`), causing **zero live articles or snippets** to reach the LLM.
  - **Root Cause 2 (FAISS Static Blindspot)**: Local index of 4,209 vectors covers classic statutes and Q&A, but contains no knowledge of contemporary 2024/2026 news or parties.
  - **Root Cause 3 (Prompt Schema Pressure)**: Strictly demanding a "Case Law Summary" on contemporary news with an empty web context forced the LLM to invent fictional court rulings.
  - **Root Cause 4 (Flawed Evaluation Metric)**: Semantic similarity was computed between the analysis and the query. Any fluent hallucination repeating query keywords scored a deceptive 5.0/5.0.
  - **Root Cause 5 (Token Quota Ceiling)**: 120B model consumed 199,879 of 200,000 daily tokens on Groq, triggering HTTP 429.

- [x] **2. Fix retrieval and metadata**
  - **Files Updated**: `backend/legal_rag/retrieval.py` and `backend/agent/lawyer_agent/nodes/retriever.py`.
  - Implemented structured evidence tagging: `[DOC-i]` for FAISS documents with case names, file paths, and keywords; `[WEB-i]` for live web articles with publication titles, real URLs, and clean excerpts.
  - Formatted rich, traceable `sources` metadata dictionaries passed across `AgentState`.

- [x] **3. Update system prompt**
  - **File Updated**: `backend/legal_rag/summarizer.py` (`analysis_prompt`).
  - Added strict grounding instructions: exclusively rely on provided evidence markers; strictly forbid fabricating court judgments, benches, or fake hearing dates; prohibit citing repealed statutes (POTA 2002); mandate stating *"No formal High Court or Supreme Court ruling has been delivered on this specific matter to date"* when applicable.

- [x] **4. Repair evaluation metrics**
  - **File Updated**: `backend/legal_rag/summarizer.py` (`evaluate_analysis`).
  - Implemented an adversarial LLM auditor with strict rubrics (scoring 1.0 on ungrounded judgments).
  - Recalibrated semantic similarity to compute **Context Entailment** (similarity against retrieved research context, not query keywords).
  - **Hard Gating Rule**: If context faithfulness < 3.0, hallucination is detected, or statute verification fails, overall confidence is capped at $\le 2.5$ with a warning badge. Plausible-sounding false answers are never rewarded.

- [x] **5. Add source verification**
  - **New Module**: `backend/legal_rag/source_verifier.py`.
  - Deterministic validation of Indian statutes: flags repealed laws (POTA repealed 2004, TADA lapsed 1995, FERA repealed 1999) and guides toward active replacements (BNS, BNSS, UAPA, FEMA).
  - URL citation verification: verifies that cited URLs exist in the retrieved search results.
  - Landmark jurisprudence catalog (*D.K. Basu*, *Naveen Jindal*, *Maneka Gandhi*, *Kesavananda Bharati*, *Mazdoor Kisan Shakti Sangathan*, etc.).
  - Emits verification badges directly appended to final responses.

- [x] **6. Run regression tests**
  - **Test Suite**: `backend/test_regression.py`.
  - **Test 1**: Source verifier catches repealed statutes (POTA, TADA) and ungrounded cases -> **PASSED**.
  - **Test 2**: Source verifier confirms valid statutes and landmark precedents -> **PASSED**.
  - **Test 3**: Retrieval traceability extracts 11 structured sources with `[DOC-i]` and `[WEB-i]` markers -> **PASSED**.
  - **Test 4**: Contemporary query (Saurav Das Jantar Mantar) retrieves real news, zero POTA hallucinations, and includes audit summary -> **PASSED**.
  - **Test 5**: Classic legal landmark query (D.K. Basu arrest guidelines) synthesizes correct guidelines -> **PASSED**.
  - **All 5 automated regression tests passed with 0 errors.**

