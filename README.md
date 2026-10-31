# ⚖️ L.A.R.A – Legal Analysis Research Assistant

**L.A.R.A (Legal Analysis & Research Assistant)** is a **deployed, AI-powered legal research system for Indian law** that automates issue identification, case retrieval, statutory analysis, and structured legal drafting using a **multi-agent RAG architecture**.

🔗 **Live Streamlit Demo:** <https://legal-assistant-research-analysis-bjcvzfrcbmvlczalv6zk9k.streamlit.app/>  

---

## 🧠 Overview
**L.A.R.A (Legal Analysis & Research Assistant)** is an intelligent, Python-based system designed to support lawyers, researchers, and citizens in conducting in-depth legal research under Indian law.

Built on the concept of autonomous legal research agents, L.A.R.A automates the complete research pipeline—transforming natural-language queries into law-aware search terms, retrieving authoritative legal sources, and generating structured, citable legal analysis. Each response is automatically self-evaluated with a real-time calibrated confidence score to improve reliability and trust.

The system leverages **LangGraph** for modular, multi-agent orchestration and **Retrieval-Augmented Generation (RAG)** to combine internal legal corpora (FAISS vector store) with live web data (Tavily Search API).

L.A.R.A supports two distinct workflows:
- **Citizen Mode**: Simplified legal guidance focused on awareness, rights, and procedures.
- **Lawyer Mode**: Professional-grade legal analysis with multi-node iterative reasoning (issue extraction, planning, retrieval, drafting, self-critique, and finalization).

---

## 🚀 Features

- **Intelligent Query Rewriting**  
  Converts user queries into law-aware, retrieval-optimized search prompts.

- **Role-Based Multi-Agent Workflows**
  - **Citizen Mode:** General legal awareness using RAG + hybrid retrieval.
  - **Lawyer Mode:** Multi-node LangGraph workflow with issue extraction, planning, retrieval, drafting, critique, and refinement.

- **Hybrid Data Retrieval**  
  Combines FAISS-based vector search with live web lookup (Tavily Search API).

- **Iterative Multi-Agent Reasoning**  
  Lawyer mode dynamically refines answers through up to 3 critique iterations.

- **Structured Legal Analysis & Citations**  
  Synthesizes statutes, acts, and case law into clear, referenced outputs with full traceability.

- **Calibrated Hybrid Confidence Evaluation**  
  Combines LLM evaluation (60%) and calibrated semantic similarity (40%) to provide an in-line confidence score (1.0 - 5.0 / 5) for every response.

---

## 🧠 Architecture Overview

```
User Query
    │
    ▼
Query Rewriter (Law-Aware Prompting)
    │
    ▼
Issue Extractor & Planner Node
    │
    ▼
Hybrid Retriever (FAISS Vector Store + Tavily Web API)
    │
    ▼
Drafting Agent Node
    │
    ▼
Critic / Self-Evaluation Node (Iterative Refinement)
    │
    ▼
Final Answer + Calibrated Confidence Score
```

---

## 🧰 Tech Stack

| Component | Technology Used |
|------------|----------------|
| **Backend Framework** | FastAPI (Python 3.11) |
| **Agent Orchestration** | LangGraph (StateGraph with MemorySaver) |
| **Lawyer Agent Nodes** | Issue Extractor, Planner, Retriever, Drafter, Critic, Finalizer |
| **Embeddings + Vector DB** | FAISS Vector Store (`sentence-transformers/paraphrase-MiniLM-L3-v2`) |
| **Language Model** | Groq (LLaMA 3.1–8B Instant) |
| **Web Search API** | Tavily Search API |
| **In-line Evaluation** | Hybrid Model (60% LLM-as-a-Judge + 40% Calibrated Cosine Similarity) |
| **Frontend** | React + Vite + Tailwind CSS + Clerk Auth |
| **Standalone UI** | Streamlit |

---

## 🏗️ Project Structure

```
Legal-Assistant-Research-Analysis/
│
├── backend/
│   ├── agent/
│   │   ├── citizen_agent.py
│   │   ├── lawyer_agent/
│   │   │   ├── nodes/
│   │   │   │   ├── issue_extractor.py
│   │   │   │   ├── planner.py
│   │   │   │   ├── retriever.py
│   │   │   │   ├── drafter.py
│   │   │   │   └── critic.py
│   │   │   ├── legacy_answer.py
│   │   │   └── state.py
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
│   │
│   ├── .env.example
│   ├── app.py
│   ├── db.py
│   ├── streamlit_app.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
├── .python-version
├── runtime.txt
├── requirements.txt
└── README.md
```

---

## 📊 Example Queries

- *The Securities and Exchange Board of India (SEBI) Act, 1992.*
- *Foreign Exchange Management Act (FEMA), 1999.*
- *Summarize the judgment in Chunna @ Charan Singh vs State of M.P.*
- *Explain Section 2A introduced in the Railways Amendment Act, 2025.*
- *The Insolvency and Bankruptcy Code (IBC).*
- *Compare provisions under IPC Sections 302 and 304B with recent case law.*

---

## 🧩 Local Setup

### 1. Clone Repository
```bash
git clone https://github.com/Shivansh-Agrawal-2727/Legal-Assistant-Research-Analysis.git
cd Legal-Assistant-Research-Analysis
```

### 2. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp backend/.env.example backend/.env
```

Add your API keys in `backend/.env`:
```env
GROQ_API_KEY="your_groq_api_key"
TAVILY_API_KEY="your_tavily_api_key"
```

Run FastAPI Backend:
```bash
python backend/app.py
```

Or run standalone Streamlit Interface:
```bash
streamlit run backend/streamlit_app.py
```

### 3. Frontend Setup (Optional React UI)
```bash
cd frontend
npm install

# Create .env from template
cp .env.example .env
```

Add keys in `frontend/.env`:
```env
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_key
VITE_API_BASE_URL=http://localhost:8000
```

Start Vite Dev Server:
```bash
npm run dev
```

---

## 🌐 Deployment

### Streamlit Community Cloud (Standalone App)
- Main File Path: `backend/streamlit_app.py`
- Python Version: `3.11`
- Configure Secrets in Streamlit Cloud Dashboard:
  ```toml
  GROQ_API_KEY = "your_groq_api_key"
  TAVILY_API_KEY = "your_tavily_api_key"
  ```

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
