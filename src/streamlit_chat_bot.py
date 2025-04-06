import asyncio
import streamlit as st
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP
import os
from datetime import datetime


# Environment variables
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# Environment variables with Docker service names
STOCK_MCP_SERVER_PORT = os.getenv("STOCK_MCP_SERVER_PORT", "8001")
STOCK_MCP_SERVER_HOST = os.getenv("STOCK_MCP_SERVER_HOST", "stock-mcp-server")  
STOCK_MCP_SERVER_URL = f"http://{STOCK_MCP_SERVER_HOST}:{STOCK_MCP_SERVER_PORT}/sse"

NEWS_MCP_SERVER_PORT = os.getenv("NEWS_MCP_SERVER_PORT", "8001")
NEWS_MCP_SERVER_HOST = os.getenv("NEWS_MCP_SERVER_HOST", "stock-mcp-server")  
NEWS_MCP_SERVER_URL = f"http://{NEWS_MCP_SERVER_HOST}:{NEWS_MCP_SERVER_PORT}/sse"


# Model lists
ANTHROPIC_MODELS = [
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307"
]

OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo"
]

# Configure MCP servers and agent
@st.cache_resource
def setup_agent(llm_provider: str, model: str):
    server_1 = MCPServerHTTP(url=STOCK_MCP_SERVER_URL)
    server_2 = MCPServerHTTP(url=NEWS_MCP_SERVER_URL)
    agent_id = f"{llm_provider}:{model}"
    return Agent(agent_id, mcp_servers=[server_1, server_2])

# Sidebar for LLM and model selection
with st.sidebar:
    st.header("Configuration")
    
    # LLM Provider selection
    llm_provider = st.selectbox(
        "Select LLM Provider",
        options=["anthropic", "openai"],
        index=0
    )
    
    # Model selection based on provider
    models = ANTHROPIC_MODELS if llm_provider == "anthropic" else OPENAI_MODELS
    selected_model = st.selectbox(
        "Select Model",
        options=models,
        index=0
    )
    
    # Display current agent configuration
    st.write(f"Current Agent: `{llm_provider}:{selected_model}`")
    api_key_input = f"{llm_provider.upper()}_API_KEY"

agent = setup_agent(llm_provider, selected_model)

# Main UI
st.title("MCP - Streamlit Chatbot")
st.markdown("Interact with your MCP servers using selected LLM")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(f"**{message['role'].capitalize()}** ({message['timestamp']}):")
        st.write(message["content"])
        if "reasoning" in message and message["reasoning"]:
            with st.expander("Reasoning"):
                st.write(message["reasoning"])

# Async function to process query
async def process_query(query: str):
    try:
        async with agent.run_mcp_servers():
            result = await agent.run(query)
            response = str(result.data)  
            reasoning = "Reasoning not available" 
            # If result has a reasoning attribute, uncomment and adjust:
            # reasoning = getattr(result, "reasoning", "Reasoning not available")
        return response, reasoning
    except Exception as e:
        import traceback
        error_details = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_details)
        return f"An error occurred: {str(e)}", "Error occurred during processing"

# Chat input
prompt = st.chat_input("Ask something:")
if prompt:
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "timestamp": timestamp
    })
    
    with st.chat_message("user"):
        st.markdown(f"**User** ({timestamp}):")
        st.write(prompt)
    
    with st.spinner("Processing..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response, reasoning = loop.run_until_complete(process_query(prompt))
            
            assistant_timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "reasoning": reasoning,
                "timestamp": assistant_timestamp
            })
            
            with st.chat_message("assistant"):
                st.markdown(f"**Assistant** ({assistant_timestamp}):")
                st.write(response)
                if reasoning and reasoning != "Reasoning not available":
                    with st.expander("Reasoning"):
                        st.write(reasoning)
        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            loop.close()

# Clear history button
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()