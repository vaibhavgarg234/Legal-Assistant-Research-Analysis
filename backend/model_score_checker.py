import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px  # type: ignore
from groq import Groq

# --- Config ---
GROQ_MODELS = ["llama3-70b-8192", "gemma-7b-it", "mixtral-8x7b-32768", "llama3-8b-8192"]

# Evaluation Data (sample queries)
EVALUATION_DATA = {
    "query": [
        "What is the process for filing a Public Interest Litigation (PIL) in India?",
        "Explain the concept of 'vicarious liability' under the Indian Penal Code.",
        "Summarize the key provisions of the 'Right to Information Act, 2005' in India.",
    ],
}


# --- Evaluation Metrics (Mock Functions) --- #
def calculate_hallucination_score(generated_text: str, context: str) -> float:
    return 0.0


def calculate_relevance_score(generated_text: str, query: str) -> float:
    return 1.0


def calculate_correctness_score(generated_text: str, ground_truth: str) -> float:
    return 1.0


def calculate_context_utilization(generated_text: str, context: str) -> float:
    return 0.9


def calculate_context_precision(generated_text: str, context: str) -> float:
    return 0.95


# --- Evaluation Pipeline --- #
def evaluate_model_on_query(model_name: str, query: str) -> dict:
    """Evaluates a model on a query. Falls back to mock scores if API unavailable."""

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": query}],
            max_tokens=512,
        )
        generated_text = response.choices[0].message.content
    except Exception:
        # If Groq API not available, mock output
        generated_text = "Mock response for testing."

    # Generate random scores for demo (replace with real metric logic)
    scores = {
        "Hallucination Score": round(np.random.uniform(0.0, 0.2), 2),
        "Relevance Score": round(np.random.uniform(0.8, 1.0), 2),
        "Correctness Score": round(np.random.uniform(0.7, 1.0), 2),
        "Context Utilization": round(np.random.uniform(0.8, 1.0), 2),
        "Context Precision": round(np.random.uniform(0.85, 1.0), 2),
    }
    return scores


# --- Streamlit UI --- #
def main():
    st.set_page_config(layout="wide", page_title="Groq Model Evaluation Dashboard")
    st.title("⚖️ Groq Model Performance Dashboard")
    st.markdown(
        "Compare the performance of different **Groq models** on legal research queries using custom metrics."
    )

    selected_query = st.selectbox(
        "Choose a query to evaluate:", EVALUATION_DATA["query"]
    )

    eval_results = []
    with st.spinner("Running model evaluations..."):
        for model in GROQ_MODELS:
            model_scores = evaluate_model_on_query(model, selected_query)
            model_scores["Model"] = model
            eval_results.append(model_scores)

    df = pd.DataFrame(eval_results).set_index("Model")

    st.subheader("📊 Evaluation Results")
    st.dataframe(df.style.highlight_max(axis=0, color="lightblue"))

    # Individual Metric Charts
    for metric in df.columns:
        st.markdown(f"### {metric}")
        st.bar_chart(df[metric])

    # Radar Chart for holistic comparison
    st.subheader("📌 Comparison across all Metrics (Radar Chart)")
    fig = px.line_polar(
        df.reset_index().melt(id_vars="Model", var_name="Metric", value_name="Score"),
        r="Score",
        theta="Metric",
        color="Model",
        line_close=True,
        markers=True,
    )
    fig.update_traces(fill="toself", opacity=0.6)
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
