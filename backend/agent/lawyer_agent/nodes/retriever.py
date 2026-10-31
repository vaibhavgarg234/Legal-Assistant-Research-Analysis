import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from typing import List

from ..state import LawyerAgentState


def legal_database_search(query: str) -> str:
    """Search FAISS for a query, return content string."""
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        possible_paths = [
            str(base_dir / "data" / "faiss_index"),
            "backend/data/faiss_index",
            "data/faiss_index",
        ]
        faiss_path = next((p for p in possible_paths if os.path.exists(p)), "data/faiss_index")
        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        db = FAISS.load_local(
            faiss_path, embedding_model, allow_dangerous_deserialization=True
        )

        retrieved_docs = db.similarity_search_with_score(query, k=5)
        content = ""
        for doc, score in retrieved_docs:
            content += doc.page_content + "\n\n"
        return content
    except Exception as e:
        return f"Error during legal database search: {e}"


def web_search(query: str) -> str:
    """Perform web search using Tavily."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY environment variable not set.")

    web_search_tool = TavilySearch(max_results=5, tavily_api_key=tavily_api_key)
    raw_results = web_search_tool.invoke(query)

    pieces = []
    if isinstance(raw_results, dict):
        items = raw_results.get("results", [])
    elif isinstance(raw_results, list):
        items = raw_results
    else:
        items = [raw_results] if raw_results else []

    for idx, item in enumerate(items, 1):
        if isinstance(item, dict):
            title = item.get("title", "Web Source")
            url = item.get("url", "")
            snippet = item.get("content", "") or item.get("snippet", "")
            if snippet:
                pieces.append(f"[WEB-{idx}] Source: {title} ({url})\nSnippet: {snippet.strip()}")
        elif isinstance(item, str) and item.strip():
            pieces.append(f"[WEB-{idx}] {item.strip()}")

    return "\n\n---\n\n".join(pieces) if pieces else "No web results found."


def retriever(state: LawyerAgentState) -> dict:
    """Retrieve context for each sub-query and merge into retrieved_context."""
    print("---RETRIEVING CONTEXT---")
    sub_queries = state["sub_queries"]

    retrieved_context = []
    for sub_query in sub_queries:
        print(f"Retrieving for: {sub_query}")
        faiss_result = legal_database_search(sub_query)
        web_result = web_search(sub_query)
        combined = f"Sub-query: {sub_query}\nFAISS: {faiss_result}\nWeb: {web_result}\n"
        retrieved_context.append(combined)

    return {"retrieved_context": retrieved_context}
