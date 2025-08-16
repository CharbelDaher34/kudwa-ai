import streamlit as st
import requests
import json
import os
from datetime import datetime
from typing import Optional, List, Dict

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://app:8430")
if not API_BASE_URL.startswith("http"):
    API_BASE_URL = f"https://{API_BASE_URL}.onrender.com"
    
    
st.set_page_config(
    page_title="Financial Data Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def make_api_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
    """Make an API request and handle errors."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, json=data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, params=params)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to the API server. Make sure it's running on " + API_BASE_URL)
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ API Error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return None

def health_check():
    """Check if the API is healthy."""
    result = make_api_request("GET", "/health")
    return result and result.get("status") == "ok"

def create_conversation(topic: Optional[str] = None):
    """Create a new conversation."""
    params = {"topic": topic} if topic else {}
    return make_api_request("POST", "/conversations", params=params)

def list_conversations():
    """List all conversations."""
    return make_api_request("GET", "/conversations")

def get_conversation(conv_id: int):
    """Get a specific conversation."""
    return make_api_request("GET", f"/conversations/{conv_id}")

def list_messages(conv_id: int):
    """List messages in a conversation."""
    return make_api_request("GET", f"/conversations/{conv_id}/messages")

def create_message(conv_id: int, content: str, sender_type: str = "user", sender: Optional[str] = None):
    """Create a new message in a conversation."""
    params = {
        "content": content,
        "sender_type": sender_type
    }
    if sender:
        params["sender"] = sender
    return make_api_request("POST", f"/conversations/{conv_id}/messages", params=params)

def ask_question(conv_id: int, prompt: str, sender: Optional[str] = None):
    """Ask a question to the LLM."""
    params = {
        "conv_id": conv_id,
        "prompt": prompt
    }
    if sender:
        params["sender"] = sender
    return make_api_request("POST", "/ask", params=params)

def main():
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2e8b57);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .conversation-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin-bottom: 1rem;
    }
    
    .message-container {
        max-height: 60vh;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        background: #ffffff;
    }
    
    .welcome-container {
        text-align: center;
        padding: 3rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 15px;
        margin: 2rem 0;
    }
    
    .sidebar-info {
        background: #e9ecef;
        padding: 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }
    
    .conversation-button {
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>💬 Financial Data Chat Assistant</h1>
        <p>Your AI-powered financial data analysis companion</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'selected_conversation_id' not in st.session_state:
        st.session_state.selected_conversation_id = None
    if 'conversations' not in st.session_state:
        st.session_state.conversations = []
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Load conversations
    conversations = list_conversations()
    # API may return an empty list (no conversations). Only treat None as an error.
    st.session_state.conversations = conversations if conversations is not None else []
    
    # Sidebar for conversations
    with st.sidebar:
        st.markdown("### 💬 Conversations")
        
        # Create new conversation section
        with st.expander("➕ Create New Conversation", expanded=False):
            new_topic = st.text_input(
                "Conversation Topic:",
                placeholder="e.g., Q3 Financial Analysis",
                key="new_topic"
            )
            if st.button("Create", use_container_width=True, type="primary"):
                with st.spinner("Creating new conversation..."):
                    result = create_conversation(new_topic if new_topic else None)
                    if result:
                        st.session_state.selected_conversation_id = result['id']
                        st.success("✅ Conversation created!")
                        st.rerun()
        
        st.markdown("---")
        
        # Quick create button for immediate use
        if st.button("🚀 Quick Start Chat", use_container_width=True, type="secondary"):
            with st.spinner("Creating conversation..."):
                result = create_conversation("Quick Chat")
                if result:
                    st.session_state.selected_conversation_id = result['id']
                    st.rerun()
        
        st.markdown("---")
        
        # List existing conversations
        if st.session_state.conversations:
            st.markdown("**📝 Your Conversations:**")
            for conv in st.session_state.conversations:
                # Some conversations may have a topic key whose value is None. Fallback to generic label.
                topic = conv.get('topic') or f"Chat {conv['id']}"
                if isinstance(topic, str) and len(topic) > 25:
                    topic = topic[:22] + "..."
                
                # Check if this is the selected conversation
                is_selected = st.session_state.selected_conversation_id == conv['id']
                
                # Create conversation button with visual indicator
                button_text = f"{'🔵' if is_selected else '⚪'} {topic}"
                
                if st.button(
                    button_text,
                    key=f"conv_{conv['id']}",
                    use_container_width=True,
                    help=f"Conversation ID: {conv['id']}"
                ):
                    st.session_state.selected_conversation_id = conv['id']
                    st.rerun()
                
                # Show additional info for selected conversation
                if is_selected:
                    st.markdown(f"""
                    <div class="sidebar-info">
                        📍 Active conversation<br>
                        🆔 ID: {conv['id']}<br>
                        📅 Created: {conv.get('created_at', 'Unknown')[:16] if conv.get('created_at') else 'Unknown'}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("💭 No conversations yet.\nCreate one to start chatting!")
        
        st.markdown("---")
        
        # System status section
        st.markdown("### 🔧 System Status")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍", help="Check API Health", use_container_width=True):
                if health_check():
                    st.success("✅ Online")
                else:
                    st.error("❌ Offline")
        
        with col2:
            if st.button("🔄", help="Refresh Conversations", use_container_width=True):
                conversations = list_conversations()
                # Update the session state even if the list is empty. None indicates an error.
                st.session_state.conversations = conversations if conversations is not None else []
                st.rerun()
        
        # Connection info
        with st.expander("ℹ️ Connection Details"):
            st.code(f"API: {API_BASE_URL}")
            st.caption("Backend connection status")
    
    # Main chat interface
    if st.session_state.selected_conversation_id:
        conv_id = st.session_state.selected_conversation_id

        # Get conversation details
        conversation = next((c for c in st.session_state.conversations if c['id'] == conv_id), None)
        if conversation:
            topic = conversation.get('topic') or f"Conversation {conv_id}"
            st.subheader(f"💬 {topic}")
        else:
            st.subheader(f"💬 Conversation {conv_id}")

        # Load messages (note: an empty list means "no messages", which should clear previous messages)
        messages = list_messages(conv_id)
        st.session_state.messages = messages if messages is not None else []

        # Display messages in a container with scrolling
        st.markdown('<div class="message-container">', unsafe_allow_html=True)
        
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg['sender_type'] == 'user':
                    with st.chat_message("user", avatar="👤"):
                        sender_name = msg.get('sender', 'User')
                        st.write(f"**{sender_name}**")
                        st.markdown(msg['content'])
                        st.caption(f"Sent: {msg['sent_time']}")
                
                elif msg['sender_type'] == 'system':
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write("**AI Assistant**")
                        st.markdown(msg['content'])
                        
                        # Show usage info if available
                        if msg.get('usage'):
                            with st.expander("📊 Usage Statistics"):
                                usage = msg['usage']
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("Requests", usage.get('requests', 'N/A'))
                                col2.metric("Request Tokens", usage.get('request_tokens', 'N/A'))
                                col3.metric("Response Tokens", usage.get('response_tokens', 'N/A'))
                                col4.metric("Total Tokens", usage.get('total_tokens', 'N/A'))
                        
                        st.caption(f"Sent: {msg['sent_time']}")
        else:
            st.info("👋 No messages yet. Start a conversation by typing below!")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Chat input at the bottom
        st.markdown("---")
        
        # Input form
        with st.form("chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_input = st.text_area(
                    "Ask a question about financial data:",
                    placeholder="Type your message here...",
                    height=100,
                    key="user_input"
                )
            
            with col2:
                st.write("")  # Add some spacing
                st.write("")  # Add some spacing
                sender_name = st.text_input(
                    "Your name:",
                    placeholder="Optional",
                    key="sender_name"
                )
                
                send_button = st.form_submit_button(
                    "💬 Send",
                    type="primary",
                    use_container_width=True
                )
            
            if send_button and user_input.strip():
                with st.spinner("🤔 AI is thinking..."):
                    result = ask_question(
                        conv_id,
                        user_input,
                        sender_name if sender_name else None
                    )
                    if result:
                        # Refresh messages after sending. If API returns an empty list, clear messages.
                        messages = list_messages(conv_id)
                        st.session_state.messages = messages if messages is not None else []
                        st.rerun()
            elif send_button and not user_input.strip():
                st.warning("Please enter a message before sending.")
    
    else:
        # No conversation selected
        st.markdown("""
        <div class="welcome-container">
            <h2>👋 Welcome to Financial Data Chat!</h2>
            <p style="font-size: 18px; color: #666; margin: 1rem 0;">
                Select a conversation from the sidebar or create a new one to get started.
            </p>
            <p style="font-size: 16px; color: #888;">
                Ask questions about financial data, get insights, and explore your datasets through natural language.
            </p>
            <div style="margin-top: 2rem;">
                <h3 style="color: #1f4e79;">💡 What you can do:</h3>
                <ul style="text-align: left; display: inline-block; color: #555;">
                    <li>📊 Analyze financial datasets</li>
                    <li>📈 Generate reports and insights</li>
                    <li>💹 Query market data</li>
                    <li>🔍 Explore trends and patterns</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
