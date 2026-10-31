# LARA/legal_rag/query_rewriter.py

import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import TypedDict, Annotated, List, Any
import operator
from dotenv import load_dotenv

load_dotenv()


class AgentState(TypedDict):
    query: str
    intermediate_steps: Annotated[List[Any], operator.add]
    web_search_results: str
    faiss_search_results: str
    final_analysis: str
    role: str  # <-- NEW: Add a role field


def rewrite_query(state: AgentState) -> dict:
    """
    Rewrites the user's natural language query into a precise legal search query,
    tailored to the user's role.
    """
    print("---REWRITING QUERY---")
    query = state["query"]
    role = state.get("role", "Common Citizen")  # <-- Use the new role field

    groq_api_key = os.getenv("GROQ_API_KEY")
    primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    fallback_model = "openai/gpt-oss-20b" if primary_model != "openai/gpt-oss-20b" else "qwen/qwen3.8-27b"

    primary_llm = ChatGroq(model=primary_model, temperature=0.2, groq_api_key=groq_api_key)
    fallback_llm = ChatGroq(model=fallback_model, temperature=0.2, groq_api_key=groq_api_key)
    llm = primary_llm.with_fallbacks([fallback_llm])

    if role == "Lawyer":
        # Prompt specifically for lawyers seeking precedents and arguments
        rewrite_prompt_template = """
You are a specialized legal research assistant for lawyers.
Your task is to rewrite the user's case details into a precise search query for legal precedents, relevant acts, and strong arguments.
Focus on extracting key entities like legal acts, case names, and specific arguments (e.g., "defense for X offense," "arguments against X").

Output MUST be JSON in this format:
{{ "rewritten_query": "<your query here>" }}

Original Case Details: {query}
JSON Output:
"""
    else:
        # Original prompt for common citizens
        rewrite_prompt_template = """
You are a legal research assistant specializing in Indian law.
Rewrite the user's query into a precise, legally-focused search query.

Output MUST be JSON in this format:
{{ "rewritten_query": "<your query here>" }}

Original Query: {query}
JSON Output:
"""

    rewrite_prompt = PromptTemplate(
        template=rewrite_prompt_template,
        input_variables=["query"],
    )

    try:
        rewriter_chain = rewrite_prompt | llm | JsonOutputParser()
        rewritten_query = rewriter_chain.invoke({"query": query})
    except Exception as e:
        print(f"JSON parsing failed, using raw string. Error: {e}")

        # --- FIX: Pass the query string directly to the LLM's chain ---
        raw_text_chain = (
            PromptTemplate(template="{query}", input_variables=["query"]) | llm
        )

        rewritten_text = raw_text_chain.invoke({"query": query})

        # Ensure the output is a string before putting it in the dictionary
        rewritten_query = {"rewritten_query": str(rewritten_text.content)}

    print(f"Rewritten Query: {rewritten_query}")
    return rewritten_query
