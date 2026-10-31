# ⚖️ L.A.R.A – Legal Analysis Research Assistant

**L.A.R.A (Legal Analysis & Research Assistant)** is a **deployed, AI-powered legal research system for Indian law** that automates issue identification, case retrieval, statutory analysis, and structured legal drafting using a **multi-agent RAG architecture**.

🔗 **Live Streamlit Demo:** <https://lara-legal-assistant.streamlit.app/>  


## 🧠 Overview
**L.A.R.A (Legal Analysis & Research Assistant)** is an intelligent, Python-based backend system designed to support lawyers, researchers, and citizens in conducting in-depth legal research under Indian law.

Built on the concept of autonomous legal research agents, L.A.R.A automates the complete research pipeline—transforming natural-language queries into law-aware search terms, retrieving authoritative legal sources, and generating structured, citable legal analysis. Each response is automatically self-evaluated with a real-time confidence score to improve reliability and trust.

The system leverages LangGraph for modular, multi-agent orchestration and Retrieval-Augmented Generation (RAG) to combine internal legal corpora with live web data.
In Lawyer Mode, L.A.R.A executes a sophisticated multi-node workflow involving issue extraction, planning, iterative retrieval, drafting, and self-critique, ensuring refined, high-quality legal outputs.

L.A.R.A supports two distinct workflows:

Citizen Mode: Simplified legal guidance focused on awareness, rights, and procedures.

Lawyer Mode: Professional-grade legal analysis with iterative reasoning, citations, and evaluation.

---

## 🚀 Features

- **Intelligent Query Rewriting**  
  Converts user queries into law-aware, retrieval-optimized search prompts.

- **Role-Based Agents**
  - **Citizen Mode:** General legal awareness using RAG + hybrid retrieval.
  - **Lawyer Mode:** Multi-node LangGraph workflow with issue extraction, planning, retrieval, drafting, critique, and refinement.

- **Hybrid Data Retrieval**  
  Combines FAISS-based vector search with live web lookup (Tavily Search API).

- **Iterative Multi-Agent Reasoning**  
  Lawyer mode dynamically refines answers through up to 3 critique iterations.

- **Structured Legal Analysis**  
  Synthesizes statutes, acts, and case law into clear, referenced outputs.

- **Citation System**  
  Each response includes citations for traceability and verification.

- **In-line Confidence Score**  
  Evaluates relevance, faithfulness, and clarity for every response.

- **Evaluation System**  
  Computes precision@5, recall@5, citation correctness, hallucination rate, and answer consistency.

- **ML Models**
  - Issue classifier: TF-IDF + Logistic Regression  
  - Semantic similarity: Sentence-Transformers

- **Test Endpoint**  
  Dedicated `/test_lawyer_agent` endpoint for validating lawyer workflows.

---
## 🧠 Architecture Overview
```
User Query
↓
Query Rewriter
↓
Issue Extractor
↓
Hybrid Retriever (FAISS + Web)
↓
Drafting Agent
↓
Critic / Self-Evaluation Agent
↓
Final Answer + Confidence Score
```
---

## 🧰 Tech Stack

| Component | Technology Used |
|------------|----------------|
| **Backend Framework** | FastAPI (Python) |
| **Agent Orchestration** | LangGraph (StateGraph with MemorySaver) |
| **Lawyer Agent Nodes** | Issue Extractor, Planner, Retriever, Drafter, Critic, Finalizer |
| **Embeddings + Search** | FAISS Vector Store |
| **Language Model** | Groq (LLaMA 3.1–8B Instant) |
| **Embeddings (Vector DB)** | HuggingFace Embeddings (all-MiniLM-L6-v2) |
| **Embeddings (Evaluation)** | Sentence-Transformers |
| **APIs Used** | Tavily Search API |
| **In-line Evaluation** | LLM-as-a-Judge (Groq) + Semantic Similarity |
| **Frontend** | React + Tailwind CSS + Clerk Auth |
| **Evaluation Metrics** | Precision@5, Recall@5, Citation Correctness, Hallucination Rate, Answer Consistency |
| **ML Models** | TF-IDF + LogisticRegression (Classifier), Sentence-Transformers (Similarity) |

---

## 🏗️ Project Structure

```
L.A.R.A-Legal-Analysis-Research-Agent/
│
├── backend/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── citizen_agent.py
│   │   ├── lawyer_agent/
│   │   │   ├── __init__.py
│   │   │   ├── state.py
│   │   │   ├── legacy_answer.py
│   │   │   └── nodes/
│   │   │       ├── issue_extractor.py
│   │   │       ├── planner.py
│   │   │       ├── retriever.py
│   │   │       ├── drafter.py
│   │   │       └── critic.py
│   │   └── router.py
│   │
│   ├── data/
│   │   ├── faiss_index/
│   │   ├── indian_law_docs/
│   │   └── data_converter.py
│   │
│   ├── legal_rag/
│   │   ├── query_rewriter.py
│   │   ├── retrieval.py
│   │   └── summarizer.py
│   ├── raw_data/
│   │
│   ├── .env
│   ├── app.py
│   ├── db.py
│   ├── model_score_checker.py
│
├── frontend/
│   ├── src/
│   └── index.html
│
├── .gitignore
└── README.md

```
---
## 📊 Example Queries
- The Securities and Exchange Board of India (SEBI) Act, 1992.
- Foreign Exchange Management Act (FEMA), 1999
- Summarize the judgment in Chunna @ Charan Singh vs State of M.P.
- Explain Section 2A introduced in the Railways Amendment Act, 2025.
- The Insolvency and Bankruptcy Code (IBC).
- Compare provisions under IPC Sections 302 and 304B with recent case law.
---


## 🧩 Local Setup

```bash
git clone https://github.com/sachin-m15/LARA-legal-Assistant.git
cd LARA-legal-Assistant/backend
pip install -r requirements.txt
```
Create .env:
```
GROQ_API_KEY=your_key
TAVILY_API_KEY=your_key
```
Run backend:
```
python app.py
```
To run the Streamlit UI (standalone alternative to React frontend):
```
streamlit run backend/streamlit_app.py
```
Frontend:
```
cd frontend
npm install
npm run dev
```
    The frontend includes user authentication via Clerk, chat history management, and role-based agent selection (Citizen or Lawyer).
---


## 🧩 Future Enhancements
- Multi-document legal reasoning across statutes and case law
- Integration with authoritative Indian legal sources (e.g., Indian Kanoon, Law Commission)
- Legal entity recognition and precedent-strength scoring
- Explainable agent reasoning and human-in-the-loop review for professionals

---

## 🏁 Contributing
Pull requests are welcome!
To contribute:
```bash
git checkout -b feature/your-feature
git commit -m "Add feature: your-feature"
git push origin feature/your-feature
```

> 💡 *“Alone we can do so little; together we can do so much.” – Helen Keller*

  
