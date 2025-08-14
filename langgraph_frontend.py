import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import uuid
from dotenv import load_dotenv

load_dotenv()

model = ChatOpenAI()

#-------------------------- Helper Functions --------------------------

def generate_thread_id():
    """Generate a new UUID for a thread."""
    return str(uuid.uuid4())

def reset_chat():
    """Reset current chat with new thread ID and empty history."""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(thread_id)
    st.session_state['message_history'] = []
    st.session_state['chat_titles'][thread_id] = "New Conversation"

def add_thread(thread_id):
    """Add thread to list if not already present."""
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    """Load messages from chatbot backend."""
    return chatbot.get_state(config={'configurable': {'thread_id': thread_id}}).values['messages']

def generate_title_from_conversation(messages):
    """Generate a short title from conversation using LLM."""
    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    prompt = f"Summarise this conversation in under 6 words:\n{conversation_text}\nTitle:"
    # Simple synchronous call to LLM backend (can replace with OpenAI API)
    response = model.invoke([HumanMessage(content=prompt)])
    return response.content.strip()

#-------------------------- Initialize Session State --------------------------

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

if 'chat_titles' not in st.session_state:
    st.session_state['chat_titles'] = {}

# Add current thread to list if not already there
add_thread(st.session_state['thread_id'])

# Set up current config
CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}

#-------------------------- Sidebar UI --------------------------

st.sidebar.title('Chandra GPT')

# New Chat Button
if st.sidebar.button("🆕 New Chat"):
    reset_chat()

# Show all threads
st.sidebar.header("💬 My Conversations")
for thread_id in st.session_state['chat_threads']:
    title = st.session_state['chat_titles'].get(thread_id, f"Thread {thread_id}")
    if st.sidebar.button(title, key=str(thread_id)):
        # Load the selected thread
        st.session_state['thread_id'] = thread_id
        CONFIG['configurable']['thread_id'] = thread_id
        loaded_messages = load_conversation(thread_id)

        # Convert Langchain message objects to simple dicts
        st.session_state['message_history'] = [
            {'role': 'user' if msg.type == 'human' else 'assistant', 'content': msg.content}
            for msg in loaded_messages
        ]

#-------------------------- Display Chat History --------------------------

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#-------------------------- User Input Handling --------------------------

user_input = st.chat_input("Type here...")

if user_input:
    # Show user message in chat
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # Call chatbot backend and stream assistant response
    with st.chat_message('assistant'):
        ai_response = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )

    # Save assistant response to history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_response})


    if len(st.session_state['message_history']) == 4:
        title = generate_title_from_conversation(st.session_state['message_history'])
        st.session_state['chat_titles'][st.session_state['thread_id']] = title
