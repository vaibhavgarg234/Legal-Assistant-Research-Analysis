import streamlit as st
import uuid
from dotenv import load_dotenv
import os
import sys

# Ensure backend directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Import the route_query function and db helpers
from agent.router import route_query
from db import get_user_threads, get_thread_messages, delete_thread, save_thread

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_logo_path = os.path.join(_backend_dir, "..", "frontend", "public", "logo.png")
if not os.path.exists(_logo_path):
    _logo_path = "⚖️"

st.set_page_config(
    page_title="L.A.R.A. - Legal Analysis & Research Assistant",
    page_icon=_logo_path,
    layout="wide",
)

# Custom CSS for fancy UI
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.2em;
        margin-bottom: 10px;
    }
    .welcome-text {
        font-size: 1.1em;
        color: #555;
        text-align: center;
        margin-bottom: 25px;
    }
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 12px;
    }
    .chat-history-card {
        padding: 8px 12px;
        border-radius: 8px;
        background-color: #f1f5f9;
        margin-bottom: 6px;
        border: 1px solid #e2e8f0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state for multi-turn conversational memory
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar: Controls & Chat History
with st.sidebar:
    st.markdown("### ⚖️ L.A.R.A. Controls")
    
    # New chat button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("⚙️ Settings")
    role = st.selectbox(
        "Select your role:",
        ["citizen", "lawyer"],
        key="role",
        help="Citizen mode provides general guidance, Lawyer mode offers detailed legal analysis.",
    )

    st.markdown("---")
    st.subheader("📜 Chat History")
    
    # Load past conversations from SQLite database
    past_threads = get_user_threads("default_user")
    if past_threads:
        for t in past_threads[:15]:
            t_id = t["thread_id"]
            t_title = t.get("title", "Untitled Chat")
            is_active = (t_id == st.session_state.thread_id)
            
            col_btn, col_del = st.columns([5, 1])
            with col_btn:
                btn_display = f"{'👉 ' if is_active else '💬 '}{t_title[:28]}"
                if st.button(btn_display, key=f"btn_{t_id}", use_container_width=True):
                    st.session_state.thread_id = t_id
                    # Load thread messages from database
                    db_msgs = get_thread_messages(t_id)
                    st.session_state.messages = []
                    for m in db_msgs:
                        st.session_state.messages.append({
                            "role": "user" if m["role"] == "user" else "assistant",
                            "content": m["content"]
                        })
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{t_id}", help="Delete chat"):
                    delete_thread(t_id)
                    if st.session_state.thread_id == t_id:
                        st.session_state.thread_id = str(uuid.uuid4())
                        st.session_state.messages = []
                    st.rerun()
    else:
        st.caption("No saved chats yet. Start chatting to save conversations!")

    st.markdown("---")
    st.subheader("💡 Example Queries")
    st.markdown("""
    - *What are the arrest guidelines under D.K. Basu v. State of West Bengal?*
    - *What happens if the police violate these guidelines?* (Follow-up)
    - *What is Section 14 of the Insolvency and Bankruptcy Code (IBC)?*
    - *What is the penalty if a creditor breaches this moratorium?* (Follow-up)
    """)

# Main Chat View
st.markdown(
    '<h1 class="main-header">⚖️ L.A.R.A. - Legal Analysis & Research Assistant</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="welcome-text">Ask legal questions and follow-ups. Context from previous turns is automatically remembered.</p>',
    unsafe_allow_html=True,
)

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask a legal question or follow-up..."):
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Use the persistent thread_id for multi-turn continuity
    active_thread_id = st.session_state.thread_id

    # Auto-register thread in DB with the first query title
    save_thread(
        user_id="default_user",
        thread_id=active_thread_id,
        title=prompt[:50] + ("..." if len(prompt) > 50 else "")
    )

    with st.spinner("🔍 Analyzing query with conversational context..."):
        try:
            # Route query with persistent thread_id so route_query loads prior turns
            result = route_query(
                role=role,
                user_query=prompt,
                thread_id=active_thread_id,
            )

            final_analysis = result.get(
                "final_analysis",
                "Sorry, no analysis could be generated.",
            )

            # Add assistant response to session state
            st.session_state.messages.append(
                {"role": "assistant", "content": final_analysis}
            )
            with st.chat_message("assistant"):
                st.markdown(final_analysis)

            # Re-render to update chat history in sidebar
            st.rerun()

        except Exception as e:
            error_msg = f"Error processing query: {e}"
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )
            with st.chat_message("assistant"):
                st.markdown(error_msg)
