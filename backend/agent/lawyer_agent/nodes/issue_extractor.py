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


def issue_extractor(state: LawyerAgentState) -> dict:
    """Extract structured legal issues and facts from the user query."""
    print("---EXTRACTING ISSUES AND FACTS---")
    query = state["query"]

    llm = get_llm()
    prompt = PromptTemplate(
        template="""You are a legal assistant. Analyze the following legal query and extract:

1. **Legal Issues**: List the key legal issues or questions raised.
2. **Facts**: List the relevant facts mentioned in the query.

Provide the output in JSON format:
{{
    "issues": ["issue1", "issue2", ...],
    "facts": ["fact1", "fact2", ...]
}}

Query: {query}

Output:""",
        input_variables=["query"],
    )

    response = safe_invoke(llm, prompt, {"query": query})

    try:
        data = json.loads(response)
        issues = data.get("issues", [])
        facts = data.get("facts", [])
    except json.JSONDecodeError:
        # Fallback: simple extraction
        issues = [query.split(".")[0]] if "." in query else [query]
        facts = []

    return {"issues": issues, "facts": facts}
