import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional, List, Dict

# Configuration
API_BASE_URL = "http://localhost:8430"  # Adjust this to match your FastAPI server

st.set_page_config(
    page_title="Financial Data Chat",
    page_icon="💬",
    layout="wide"
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
    st.title("💬 Financial Data Chat Frontend")
    st.markdown("Test the conversation and message API functionalities")
    
    # Health check
    with st.sidebar:
        st.header("🔧 System Status")
        if st.button("Check API Health"):
            if health_check():
                st.success("✅ API is healthy!")
            else:
                st.error("❌ API is not responding")
        
        st.markdown("---")
        st.markdown("**API Base URL:**")
        st.code(API_BASE_URL)
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📋 Conversations", "📝 Messages", "🧪 API Testing"])
    
    with tab1:
        st.header("Chat Interface")
        
        # Conversation selection
        conversations = list_conversations()
        if conversations:
            conv_options = {f"ID {conv['id']}: {conv.get('topic', 'No topic')}": conv['id'] 
                          for conv in conversations}
            selected_conv = st.selectbox("Select Conversation", list(conv_options.keys()))
            conv_id = conv_options[selected_conv] if selected_conv else None
        else:
            st.info("No conversations found. Create one first.")
            conv_id = None
        
        # Create new conversation
        with st.expander("➕ Create New Conversation"):
            new_topic = st.text_input("Topic (optional)")
            if st.button("Create Conversation"):
                result = create_conversation(new_topic if new_topic else None)
                if result:
                    st.success(f"✅ Created conversation with ID: {result['id']}")
                    st.rerun()
        
        # Chat interface
        if conv_id:
            st.subheader(f"Chat - Conversation {conv_id}")
            
            # Display messages
            messages = list_messages(conv_id)
            if messages:
                for msg in messages:
                    sender_icon = "🤖" if msg['sender_type'] == "system" else "👤"
                    sender_name = msg.get('sender', msg['sender_type'].title())
                    
                    with st.chat_message(msg['sender_type']):
                        st.write(f"**{sender_icon} {sender_name}**")
                        st.write(msg['content'])
                        
                        # Show usage info for system messages
                        if msg['sender_type'] == "system" and msg.get('usage'):
                            with st.expander("📊 Usage Stats"):
                                usage = msg['usage']
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("Requests", usage.get('requests', 'N/A'))
                                col2.metric("Request Tokens", usage.get('request_tokens', 'N/A'))
                                col3.metric("Response Tokens", usage.get('response_tokens', 'N/A'))
                                col4.metric("Total Tokens", usage.get('total_tokens', 'N/A'))
                        
                        st.caption(f"Sent: {msg['sent_time']}")
            
            # Input for new message
            st.markdown("---")
            user_input = st.text_area("Ask a question:", key="chat_input")
            sender_name = st.text_input("Your name (optional):", key="sender_name")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💬 Send Message", type="primary"):
                    if user_input.strip():
                        with st.spinner("Sending message..."):
                            result = ask_question(conv_id, user_input, sender_name if sender_name else None)
                            if result:
                                st.success("✅ Message sent!")
                                st.rerun()
                    else:
                        st.warning("Please enter a message")
            
            with col2:
                if st.button("🔄 Refresh Messages"):
                    st.rerun()
    
    with tab2:
        st.header("📋 Conversations Management")
        
        # Create conversation
        with st.form("create_conversation_form"):
            st.subheader("Create New Conversation")
            topic = st.text_input("Topic (optional)")
            submitted = st.form_submit_button("Create")
            
            if submitted:
                result = create_conversation(topic if topic else None)
                if result:
                    st.success(f"✅ Created conversation: {result}")
        
        # List conversations
        st.subheader("All Conversations")
        conversations = list_conversations()
        if conversations:
            for conv in conversations:
                with st.expander(f"Conversation {conv['id']}: {conv.get('topic', 'No topic')}"):
                    st.json(conv)
        else:
            st.info("No conversations found")
    
    with tab3:
        st.header("📝 Messages Management")
        
        # Select conversation
        conversations = list_conversations()
        if conversations:
            conv_options = {f"ID {conv['id']}: {conv.get('topic', 'No topic')}": conv['id'] 
                          for conv in conversations}
            selected_conv = st.selectbox("Select Conversation", list(conv_options.keys()), key="msg_conv_select")
            conv_id = conv_options[selected_conv] if selected_conv else None
            
            if conv_id:
                # Create message
                with st.form("create_message_form"):
                    st.subheader("Create New Message")
                    content = st.text_area("Message content")
                    sender_type = st.selectbox("Sender type", ["user", "system"])
                    sender = st.text_input("Sender name (optional)")
                    submitted = st.form_submit_button("Create Message")
                    
                    if submitted and content.strip():
                        result = create_message(conv_id, content, sender_type, sender if sender else None)
                        if result:
                            st.success(f"✅ Created message: {result}")
                
                # List messages
                st.subheader(f"Messages in Conversation {conv_id}")
                messages = list_messages(conv_id)
                if messages:
                    for i, msg in enumerate(messages):
                        with st.expander(f"Message {i+1}: {msg['sender_type']} - {msg['content'][:50]}..."):
                            st.json(msg)
                else:
                    st.info("No messages found")
        else:
            st.info("No conversations found. Create one first.")
    
    with tab4:
        st.header("🧪 API Testing")
        
        # Raw API testing
        st.subheader("Raw API Requests")
        
        col1, col2 = st.columns(2)
        with col1:
            method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"])
            endpoint = st.text_input("Endpoint", value="/health")
        
        with col2:
            if method in ["POST", "PUT"]:
                data = st.text_area("JSON Data (optional)", value="{}")
            else:
                data = "{}"
            params = st.text_area("Query Parameters (JSON)", value="{}")
        
        if st.button("Send Request"):
            try:
                data_dict = json.loads(data) if data.strip() else None
                params_dict = json.loads(params) if params.strip() else None
                
                result = make_api_request(method, endpoint, data_dict, params_dict)
                if result:
                    st.success("✅ Request successful!")
                    st.json(result)
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {str(e)}")
        
        # Quick actions
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🏥 Health Check"):
                result = make_api_request("GET", "/health")
                if result:
                    st.json(result)
        
        with col2:
            if st.button("📋 List Conversations"):
                result = make_api_request("GET", "/conversations")
                if result:
                    st.json(result)
        
        with col3:
            if st.button("➕ Create Test Conversation"):
                result = make_api_request("POST", "/conversations", params={"topic": "Test conversation"})
                if result:
                    st.json(result)

if __name__ == "__main__":
    main()
