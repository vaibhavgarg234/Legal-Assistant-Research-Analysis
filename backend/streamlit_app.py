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

# Import the route_query function
from agent.router import route_query

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_logo_path = os.path.join(_backend_dir, "..", "frontend", "public", "logo.png")
if not os.path.exists(_logo_path):
    _logo_path = "⚖️"

st.set_page_config(
    page_title="L.A.R.A. - Legal Analysis & Research Assistant",
    page_icon=_logo_path,
)

# Custom CSS for fancy UI
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5em;
        margin-bottom: 20px;
    }
    .welcome-text {
        font-size: 1.2em;
        color: #555;
        text-align: center;
        margin-bottom: 30px;
    }
    .chat-container {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 20px;
        background-color: #f9f9f9;
        margin-bottom: 20px;
    }
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 10px;
    }
    .stChatInput {
        border-radius: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 class="main-header">⚖️ L.A.R.A. - Legal Analysis & Research Assistant</h1>',
    unsafe_allow_html=True,
)

# Display logo
col1, col2, col3 = st.columns([1, 1, 1])
st.markdown(
    '<p class="welcome-text">Welcome to the <strong>Legal Analysis & Research Assistant</strong>. Ask your legal questions below and get AI-powered responses tailored to Indian law.</p>',
    unsafe_allow_html=True,
)

# Role selection in sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    role = st.selectbox(
        "Select your role:",
        ["citizen", "lawyer"],
        key="role",
        help="Citizen mode provides general guidance, Lawyer mode offers detailed legal analysis.",
    )

    st.header("💡 Example Queries")
    st.markdown("""
    - The Securities and Exchange Board of India (SEBI) Act, 1992.
    - Explain the Foreign Exchange Management Act (FEMA), 1999.
    - What is The Insolvency and Bankruptcy Code (IBC).
    """)

    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.header("ℹ️ About")
    st.markdown("""
    L.A.R.A. uses advanced AI agents to provide accurate legal information based on Indian laws and case precedents.
    """)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

st.subheader("💬 Chat with L.A.R.A.")

# Chat container
with st.container():
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Enter your legal query"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate a unique thread_id for this query
    thread_id = str(uuid.uuid4())

    with st.spinner("🔍 Analyzing your query..."):
        try:
            # Call the route_query function directly
            result = route_query(
                role=role,
                user_query=prompt,
                thread_id=thread_id,
            )

            final_analysis = result.get(
                "final_analysis",
                "Sorry, no analysis could be generated.",
            )

            # Add assistant response to chat history
            st.session_state.messages.append(
                {"role": "assistant", "content": final_analysis}
            )
            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(final_analysis)

            # Fun success animation
            st.balloons()

        except Exception as e:
            error_msg = f"Error processing query: {e}"
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )
            with st.chat_message("assistant"):
                st.markdown(error_msg)

st.markdown("---")
