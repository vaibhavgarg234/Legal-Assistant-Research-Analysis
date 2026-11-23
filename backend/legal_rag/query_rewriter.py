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
    role: str
    chat_history: List[Any]


def format_chat_history(chat_history: list, max_turns: int = 3) -> str:
    """Formats prior chat messages into a clean summary for context-aware prompts."""
    if not chat_history:
        return "No prior conversation history."

    recent = chat_history[-(max_turns * 2):]
    formatted = []
    for msg in recent:
        if isinstance(msg, dict):
            role = "User" if msg.get("role") in ("user", "human") else "Assistant"
            content = msg.get("content", "").strip()
        else:
            role = "User" if getattr(msg, "type", "") == "human" else "Assistant"
            content = getattr(msg, "content", "").strip()

        # Strip long audit summary if present from past bot responses to prevent token bloating
        if role == "Assistant" and "--- Evaluation & Audit Summary ---" in content:
            content = content.split("--- Evaluation & Audit Summary ---")[0].strip()

        words = content.split()
        if len(words) > 120:
            content = " ".join(words[:120]) + "..."
        if content:
            formatted.append(f"{role}: {content}")

    return "\n".join(formatted) if formatted else "No prior conversation history."


def rewrite_query(state: AgentState) -> dict:
    """
    Rewrites the user's natural language query into a precise legal search query,
    tailored to the user's role and resolving any references to previous turns in chat_history.
    """
    print("---REWRITING QUERY---")
    query = state["query"]
    role = state.get("role", "Common Citizen")
    chat_history = state.get("chat_history", [])
    history_text = format_chat_history(chat_history)

    groq_api_key = os.getenv("GROQ_API_KEY")
    primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    fallback_model = "openai/gpt-oss-20b" if primary_model != "openai/gpt-oss-20b" else "qwen/qwen3.8-27b"

    primary_llm = ChatGroq(model=primary_model, temperature=0.2, groq_api_key=groq_api_key)
    fallback_llm = ChatGroq(model=fallback_model, temperature=0.2, groq_api_key=groq_api_key)
    llm = primary_llm.with_fallbacks([fallback_llm])

    if role == "Lawyer":
        rewrite_prompt_template = """You are a specialized legal research assistant for lawyers.
Your task is to rewrite the user's latest query into a precise, standalone legal search query for precedents, acts, and arguments.

Prior Conversation History:
{chat_history}

Current User Query: {query}

INSTRUCTIONS:
1. MULTI-TURN CONTEXT RESOLUTION: If the current query is a follow-up or references previous context (e.g. using pronouns like 'these', 'this', 'they', 'the case', 'the judgment', or asking about consequences, remedies, appeals, or exceptions of the previously discussed matter), you MUST resolve those references using the Prior Conversation History. Formulate a standalone legal search query that explicitly mentions the specific statutes, judgments, or legal entities discussed.
2. NEW TOPIC: If the current query is a brand-new, unrelated topic, rewrite it focusing on the current query.
3. Extract key legal entities: legal acts, section numbers, case names, and specific arguments.

Output MUST be JSON in this format:
{{ "rewritten_query": "<your standalone query here>" }}
JSON Output:
"""
    else:
        rewrite_prompt_template = """You are a legal research assistant specializing in Indian law.
Rewrite the user's query into a precise, legally-focused search query.

Prior Conversation History:
{chat_history}

Current User Query: {query}

INSTRUCTIONS:
1. MULTI-TURN CONTEXT RESOLUTION: If the user's current query is a follow-up or asks about the previous topic (e.g. "what if they violate this?", "what are the remedies?", "what is the punishment?", "can they appeal?", "who can file this?"), you MUST use the Prior Conversation History to identify what 'this' or 'they' refers to. Produce a standalone, comprehensive search query specifying the exact case, law, or subject from the conversation history so that search tools retrieve relevant legal provisions and precedents.
2. INDEPENDENT QUERY: If the query is completely unrelated to the history, rewrite it based on the current query alone.

Output MUST be JSON in this format:
{{ "rewritten_query": "<your standalone query here>" }}
JSON Output:
"""

    rewrite_prompt = PromptTemplate(
        template=rewrite_prompt_template,
        input_variables=["query", "chat_history"],
    )

    try:
        rewriter_chain = rewrite_prompt | llm | JsonOutputParser()
        rewritten_query = rewriter_chain.invoke({"query": query, "chat_history": history_text})
    except Exception as e:
        print(f"JSON parsing failed, using raw string. Error: {e}")

        raw_text_chain = (
            PromptTemplate(
                template="Rewrite into a single standalone search query for Indian law, resolving any pronouns from history:\nHistory:\n{chat_history}\nQuery:\n{query}\nStandalone Query:",
                input_variables=["query", "chat_history"]
            ) | llm
        )

        rewritten_text = raw_text_chain.invoke({"query": query, "chat_history": history_text})
        rewritten_query = {"rewritten_query": str(rewritten_text.content).strip()}

    print(f"Rewritten Query: {rewritten_query}")
    return rewritten_query
