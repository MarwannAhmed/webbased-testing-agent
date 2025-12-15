import streamlit as st
from config import Config

# Page configuration
st.set_page_config(
    page_title="Web-based Testing Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_phase' not in st.session_state:
        st.session_state.current_phase = None
    if 'page_context' not in st.session_state:
        st.session_state.page_context = None
    if 'test_cases' not in st.session_state:
        st.session_state.test_cases = []
    if 'generated_code' not in st.session_state:
        st.session_state.generated_code = None
    if 'metrics' not in st.session_state:
        st.session_state.metrics = {
            'total_tokens': 0,
            'total_time': 0,
            'iterations': []
        }

def main():
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("🤖 Web-based Testing Agent")
    st.markdown("*Your AI-powered QA partner for test exploration, design, and implementation*")
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        # Reset button
        if st.button("🔄 Reset Agent", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.divider()
        
    # Main content area
    tab1, = st.tabs(["💬 Chat"])
    
    with tab1:
        st.subheader("Chat Interface")
        
        # Chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Enter a URL to explore or ask a question..."):
            # Add user message to session state
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Generate assistant response
            response = "🚧 Agent processing has not been implemented yet. Coming soon!"
            
            # Add assistant response to session state
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Rerun to display the updated messages
            st.rerun()

if __name__ == "__main__":
    main()