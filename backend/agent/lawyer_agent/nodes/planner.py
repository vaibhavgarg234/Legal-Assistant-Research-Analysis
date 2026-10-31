import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import json

from ..state import LawyerAgentState

load_dotenv()


def get_llm():
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable not set.")
    primary_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    fallback_model = "openai/gpt-oss-20b" if primary_model != "openai/gpt-oss-20b" else "qwen/qwen3.8-27b"

    primary_llm = ChatGroq(model=primary_model, temperature=0.2, groq_api_key=groq_api_key)
    fallback_llm = ChatGroq(model=fallback_model, temperature=0.2, groq_api_key=groq_api_key)
    return primary_llm.with_fallbacks([fallback_llm])


def safe_invoke(llm, prompt, vars):
    try:
        chain = prompt | llm
        result = chain.invoke(vars)
        return getattr(result, "content", str(result))
    except Exception as e:
        api_key = os.getenv("GROQ_API_KEY")
        for alt_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                fallback_chat = ChatGroq(model=alt_model, temperature=0.2, groq_api_key=api_key)
                chain = prompt | fallback_chat
                result = chain.invoke(vars)
                return getattr(result, "content", str(result))
            except Exception:
                continue
        raise e


def planner(state: LawyerAgentState) -> dict:
    """Convert issues and facts into 3-6 retrieval sub-queries."""
    print("---PLANNING RETRIEVAL SUB-QUERIES---")
    issues = state["issues"]
    facts = state["facts"]
    query = state["query"]

    issues_str = "\n".join(issues)
    facts_str = "\n".join(facts)

    llm = get_llm()
    prompt = PromptTemplate(
        template="""You are a legal research planner. Based on the legal issues and facts, generate 3-6 specific sub-queries for retrieving relevant legal information from databases and web searches.

Issues:
{issues}

Facts:
{facts}

Original Query: {query}

Generate sub-queries that focus on:
- Relevant statutes and sections
- Case precedents
- Legal principles
- Recent judgments

Provide output as JSON list: ["sub_query1", "sub_query2", ...]

Sub-queries:""",
        input_variables=["issues", "facts", "query"],
    )

    response = safe_invoke(
        llm, prompt, {"issues": issues_str, "facts": facts_str, "query": query}
    )

    try:
        sub_queries = json.loads(response)
        if not isinstance(sub_queries, list):
            sub_queries = [response]
    except json.JSONDecodeError:
        # Fallback: split by lines
        sub_queries = [line.strip() for line in response.split("\n") if line.strip()][
            :6
        ]

    return {"sub_queries": sub_queries}
