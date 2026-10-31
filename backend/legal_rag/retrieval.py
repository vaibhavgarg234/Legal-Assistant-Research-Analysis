# LARA/legal_rag/retrieval.py

import os
from pathlib import Path
from typing import TypedDict, Annotated, List, Any
import operator

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableParallel
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_tavily import TavilySearch

# -------------------------
# Load environment variables
# -------------------------
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

# -------------------------
# GLOBAL LAZY-LOADED OBJECTS
# -------------------------
_embedding_model = None
_faiss_db = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-MiniLM-L3-v2"  # smaller model
        )
    return _embedding_model


def get_faiss_db():
    global _faiss_db
    if _faiss_db is None:
        possible_paths = [
            str(backend_dir / "data" / "faiss_index"),
            os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index"),
            "backend/data/faiss_index",
            "data/faiss_index",
        ]
        faiss_path = next((p for p in possible_paths if os.path.exists(p)), "data/faiss_index")
        _faiss_db = FAISS.load_local(
            faiss_path,
            get_embedding_model(),
            allow_dangerous_deserialization=True,
        )
    return _faiss_db


# -------------------------
# Agent State
# -------------------------
class AgentState(TypedDict):
    query: str
    intermediate_steps: Annotated[List[Any], operator.add]
    web_search_results: str
    faiss_search_results: str
    final_analysis: str
    research_complete: bool
    chat_history: List[BaseMessage]
    sources: Annotated[List[dict], operator.add]


# -------------------------
# FAISS Legal DB Tool (LAZY SAFE)
# -------------------------
@tool
def legal_database_search(query: str) -> List[Document]:
    """
    Search against a pre-indexed FAISS vector store of Indian laws and cases.
    Returns a list of Document objects.
    """
    global faiss_db
    try:
        db = get_faiss_db()
        retrieved_docs = db.similarity_search_with_score(query, k=5)
        return [doc[0] for doc in retrieved_docs]

    except FileNotFoundError:
        return [Document(page_content="FAISS index not found.")]
    except Exception as e:
        return [Document(page_content=f"Error during legal database search: {e}")]


# -------------------------
# Research Function
# -------------------------
def perform_research(state: AgentState) -> dict:
    print("---PERFORMING RESEARCH---")
    query = state.get("rewritten_query") or state.get("query")

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY environment variable not set.")

    web_search_tool = TavilySearch(max_results=6, tavily_api_key=tavily_api_key)

    rag_chain = RunnableParallel(
        {
            "faiss_search_results": lambda x: legal_database_search.invoke(x["query"]),
            "web_search_results": lambda x: web_search_tool.invoke(x["query"]),
        }
    )

    results = rag_chain.invoke({"query": query})

    faiss_docs = results.get("faiss_search_results", [])
    raw_web_results = results.get("web_search_results", [])

    sources = []
    faiss_pieces = []

    for idx, doc in enumerate(faiss_docs, 1):
        meta = doc.metadata or {}
        case_name = meta.get("case_name", "Statutory Provision")
        source_file = meta.get("source", "Indian Legal Corpus")
        keywords = meta.get("keywords", [])
        
        piece = (
            f"[DOC-{idx}] Source: {source_file} | Topic: {case_name} | Keywords: {', '.join(keywords) if keywords else 'N/A'}\n"
            f"Content: {doc.page_content.strip()}"
        )
        faiss_pieces.append(piece)
        sources.append({
            "citation_id": f"DOC-{idx}",
            "type": "document",
            "title": case_name,
            "source_file": source_file,
            "metadata": meta,
            "content": doc.page_content.strip()[:300]
        })

    faiss_content = "\n\n---\n\n".join(faiss_pieces) if faiss_pieces else "No legal database documents retrieved."

    # Robust web extraction: handles dict {'results': [...]}, list of dicts, or strings
    web_content_pieces = []
    if isinstance(raw_web_results, dict):
        web_items = raw_web_results.get("results", [])
    elif isinstance(raw_web_results, list):
        web_items = raw_web_results
    else:
        web_items = [raw_web_results] if raw_web_results else []

    for idx, item in enumerate(web_items, 1):
        if isinstance(item, dict):
            title = item.get("title", "Web Report")
            url = item.get("url", "")
            snippet = item.get("content", "") or item.get("snippet", "")
            score = item.get("score", None)
            if snippet:
                formatted_item = (
                    f"[WEB-{idx}] Title: {title}\n"
                    f"URL: {url}\n"
                    f"Excerpt: {snippet.strip()}"
                )
                web_content_pieces.append(formatted_item)
                sources.append({
                    "citation_id": f"WEB-{idx}",
                    "type": "web",
                    "title": title,
                    "url": url,
                    "relevance_score": score,
                    "content": snippet.strip()
                })
        elif isinstance(item, str) and item.strip():
            web_content_pieces.append(f"[WEB-{idx}] {item.strip()}")
            sources.append({
                "citation_id": f"WEB-{idx}",
                "type": "web",
                "title": "Web Excerpt",
                "content": item.strip()
            })

    web_content = "\n\n---\n\n".join(web_content_pieces) if web_content_pieces else "No web results found."

    print(f"---RESEARCH COMPLETE (Indexed {len(faiss_pieces)} DOC sources, {len(web_content_pieces)} WEB sources)---")

    return {
        "faiss_search_results": faiss_content,
        "web_search_results": web_content,
        "sources": sources,
        "intermediate_steps": [
            f"FAISS Retrieval Context:\n{faiss_content[:2000]}",
            f"Live Web Context:\n{web_content[:3000]}",
        ],
    }
