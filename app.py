import streamlit as st
from config import Config
from agents.exploration_agent import ExplorationAgent
from agents.design_agent import DesignAgent
import re
import base64
from io import BytesIO
import nest_asyncio
import asyncio
import sys

# Fix for Playwright + Streamlit on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Page configuration
st.set_page_config(
    page_title="Web-based Testing Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'llm_tokens' not in st.session_state:
        st.session_state.llm_tokens = 0
    if 'total_time' not in st.session_state:
        st.session_state.total_time = 0.0
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_phase' not in st.session_state:
        st.session_state.current_phase = None
    if 'exploration_data' not in st.session_state:
        st.session_state.exploration_data = None
    if 'test_cases' not in st.session_state:
        st.session_state.test_cases = []
    if 'generated_code' not in st.session_state:
        st.session_state.generated_code = None
    if 'exploration_agent' not in st.session_state:
        st.session_state.exploration_agent = None
    if 'design_agent' not in st.session_state:
        st.session_state.design_agent = None
    if 'design_data' not in st.session_state:
        st.session_state.design_data = None
    if 'design_messages' not in st.session_state:
        st.session_state.design_messages = []

def is_url(text: str) -> bool:
    """Check if the text is a valid URL"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(text) is not None

def display_exploration_results(exploration_data: dict):
    """Display exploration results in a structured format"""
    
    # Page Information
    with st.expander("📄 Page Information", expanded=True):
        page_info = exploration_data["page_info"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("HTTP Status", page_info.get('http_status', 'N/A'))
        with col2:
            st.metric("Load Time", f"{page_info.get('load_time', 0):.2f}s")
        with col3:
            st.metric("Title", page_info.get('title', 'N/A')[:30] + "...")
    
    # Metrics Dashboard
    with st.expander("📊 Exploration Metrics", expanded=True):
        metrics = exploration_data["metrics"]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Elements Found", metrics['elements_found'])
        with col2:
            st.metric("LLM Tokens", metrics['llm_tokens'])
        with col3:
            st.metric("LLM Time", f"{metrics['llm_response_time']:.2f}s")
        with col4:
            st.metric("Total Time", f"{metrics['total_time']:.2f}s")
    
    # Interactive Elements
    with st.expander("🎯 Interactive Elements", expanded=False):
        elements = exploration_data["interactive_elements"]
        
        if elements:
            # Create summary
            element_types = {}
            for elem in elements:
                tag = elem.get("tag", "unknown")
                element_types[tag] = element_types.get(tag, 0) + 1
            
            st.write(f"**Total Elements:** {len(elements)}")
            st.write("**Distribution:**")
            
            # Display as columns
            cols = st.columns(min(len(element_types), 4))
            for idx, (tag, count) in enumerate(sorted(element_types.items(), key=lambda x: x[1], reverse=True)):
                with cols[idx % len(cols)]:
                    st.metric(tag.upper(), count)
            
            st.divider()
            
            # Show detailed table for first 10 elements
            st.write("**First 10 Elements:**")
            table_data = []
            for idx, elem in enumerate(elements[:10]):
                locator = elem.get('suggested_locators', [{}])[0]
                table_data.append({
                    "Index": idx,
                    "Tag": elem.get('tag', '').upper(),
                    "ID": elem.get('id', '-'),
                    "Text": elem.get('text', '')[:40] + "..." if elem.get('text') else '-',
                    "Best Locator": f"{locator.get('strategy', 'N/A')}"
                })
            
            st.dataframe(table_data, use_container_width=True, width='stretch')
        else:
            st.warning("No interactive elements found")
    
    # AI Analysis
    with st.expander("🤖 AI Analysis", expanded=True):
        ai_analysis = exploration_data["ai_analysis"]
        
        if "error" in ai_analysis:
            st.error(f"AI Analysis Error: {ai_analysis['error']}")
        elif "parse_error" in ai_analysis:
            st.warning("Could not parse structured analysis")
            st.text(ai_analysis.get('raw_analysis', 'N/A'))
        else:
            st.write("**Page Purpose:**")
            st.info(ai_analysis.get('page_purpose', 'N/A'))
            
            if ai_analysis.get('main_functionality'):
                st.write("**Main Functionality:**")
                for func in ai_analysis['main_functionality']:
                    st.write(f"• {func}")
            
            if ai_analysis.get('testable_areas'):
                st.write("**Testable Areas:**")
                for area in ai_analysis['testable_areas']:
                    with st.container():
                        st.write(f"**{area.get('area', 'N/A')}**")
                        st.write(f"_{area.get('description', 'N/A')}_")
                        st.divider()
            
            if ai_analysis.get('recommended_test_priority'):
                st.write("**Recommended Test Priority:**")
                for i, priority in enumerate(ai_analysis['recommended_test_priority'], 1):
                    st.write(f"{i}. {priority}")
    
    # Screenshot
    with st.expander("📸 Page Screenshot", expanded=False):
        screenshot_b64 = exploration_data.get("screenshot_base64", "")
        if screenshot_b64:
            try:
                st.image(f"data:image/png;base64,{screenshot_b64}", 
                        caption="Full Page Screenshot",
                        use_container_width=True,
                        width='stretch')
            except Exception as e:
                st.error(f"Could not display screenshot: {e}")
        else:
            st.warning("No screenshot available")
    
    # Saved Files
    if 'phase1_files' in st.session_state and st.session_state.phase1_files:
        with st.expander("💾 Saved Results", expanded=False):
            for file_type, file_path in st.session_state.phase1_files.items():
                st.text(f"{file_type}: {file_path}")

def display_design_results(design_data: dict):
    """Display design results in a structured format"""
    
    # Metrics Dashboard
    with st.expander("📊 Design Metrics", expanded=True):
        metrics = design_data["metrics"]
        coverage = design_data["coverage"]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Test Cases", metrics['total_test_cases'])
        with col2:
            st.metric("Coverage", f"{coverage['percentage']:.1f}%")
        with col3:
            st.metric("LLM Tokens", metrics['llm_tokens'])
        with col4:
            st.metric("Generation Time", f"{metrics['llm_response_time']:.2f}s")
        
        # Coverage breakdown
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Element Coverage:**")
            st.metric("Covered Elements", f"{coverage['covered_elements']} / {coverage['total_elements']}")
            st.metric("Uncovered Elements", coverage['uncovered_elements'])
        
        with col2:
            # Priority distribution
            st.markdown("**Priority Distribution:**")
            priority_dist = coverage.get('priority_distribution', {})
            for priority, count in priority_dist.items():
                st.write(f"🔹 {priority}: {count}")
            
            # Category distribution
            st.markdown("**Category Distribution:**")
            category_dist = coverage.get('category_distribution', {})
            for category, count in category_dist.items():
                st.write(f"🔸 {category}: {count}")
    
    # Test Cases Table
    with st.expander("🧪 Test Cases", expanded=True):
        test_cases = design_data["test_cases"]
        
        if test_cases:
            for tc in test_cases:
                # Create a card-like display for each test case
                priority_color = {
                    "High": "🔴",
                    "Medium": "🟡",
                    "Low": "🟢"
                }.get(tc.get("priority", "Medium"), "⚪")
                
                st.markdown(f"### {priority_color} {tc['id']}: {tc['name']}")
                
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.write(f"**Priority:** {tc.get('priority', 'N/A')}")
                    st.write(f"**Category:** {tc.get('category', 'N/A')}")
                    st.write(f"**Status:** {tc.get('status', 'pending').capitalize()}")
                
                with col2:
                    st.markdown("**Test Steps:**")
                    for idx, step in enumerate(tc.get('steps', []), 1):
                        st.write(f"{idx}. {step}")
                    
                    st.markdown(f"**Expected Result:**")
                    st.write(tc.get('expected_result', 'N/A'))
                    
                    # Show related elements
                    if tc.get('elements'):
                        with st.expander("🎯 Elements Used", expanded=False):
                            for elem in tc['elements']:
                                elem_text = elem.get('text', '')
                                elem_id = elem.get('id', '')
                                elem_name = elem.get('name', '')
                                
                                display_text = f"`{elem['tag']}`"
                                if elem_id:
                                    display_text += f" (id='{elem_id}')"
                                elif elem_name:
                                    display_text += f" (name='{elem_name}')"
                                if elem_text:
                                    display_text += f" - {elem_text}"
                                
                                st.write(f"- {display_text}")
                
                st.markdown("---")
        else:
            st.info("No test cases generated yet.")
    
    # Saved Files
    if 'phase2_files' in st.session_state and st.session_state.phase2_files:
        with st.expander("💾 Saved Results", expanded=False):
            for file_type, file_path in st.session_state.phase2_files.items():
                st.text(f"{file_type}: {file_path}")

def handle_test_generation():
    """Handle test case generation from exploration data"""
    
    # Load exploration data from file instead of session state
    exploration_data = ExplorationAgent.load_results()
    
    if not exploration_data:
        return {
            "type": "error",
            "content": "❌ No exploration data available. Please explore a URL first and ensure results are saved."
        }
    
    status_placeholder = st.empty()
    
    try:
        # Initialize design agent if not exists
        if st.session_state.design_agent is None:
            st.session_state.design_agent = DesignAgent()
        
        agent = st.session_state.design_agent
        
        # Show progress
        with status_placeholder.container():
            st.info("🧪 Generating test cases from saved exploration data...")
        
        # Generate test cases using loaded data
        result = agent.generate_test_cases(exploration_data)
        
        # Clear status
        status_placeholder.empty()
        
        if result["status"] == "error":
            return {
                "type": "error",
                "content": f"❌ Error generating test cases: {result.get('error', 'Unknown error')}"
            }
        
        # Store in session state
        st.session_state.design_data = result
        st.session_state.test_cases = result["test_cases"]
        st.session_state.current_phase = "design_complete"
        
        # Save results to phase2 directory
        saved_files = agent.save_results()
        if saved_files and "error" not in saved_files:
            st.session_state.phase2_files = saved_files
        
        return {
            "type": "success",
            "content": f"✅ Generated **{len(result['test_cases'])}** test cases with **{result['coverage']['percentage']:.1f}%** coverage.",
            "data": result
        }
        
    except Exception as e:
        status_placeholder.empty()
        return {
            "type": "error",
            "content": f"❌ Error: {str(e)}"
        }

def handle_test_refinement(feedback: str):
    """Handle test case refinement based on user feedback"""
    
    if not st.session_state.design_agent:
        return {
            "type": "error",
            "content": "❌ No design session active."
        }
    
    status_placeholder = st.empty()
    
    try:
        agent = st.session_state.design_agent
        
        with status_placeholder.container():
            st.info("🔄 Refining test cases...")
        
        result = agent.refine_test_cases(feedback)
        
        status_placeholder.empty()
        
        if result["status"] == "error":
            return {
                "type": "error",
                "content": f"❌ Error refining test cases: {result.get('error', 'Unknown error')}"
            }
        
        # Update session state
        st.session_state.design_data = result
        st.session_state.test_cases = result["test_cases"]
        
        # Save updated results to phase2 directory (overwrites previous)
        saved_files = agent.save_results()
        if saved_files and "error" not in saved_files:
            st.session_state.phase2_files = saved_files
        
        return {
            "type": "success",
            "content": f"✅ Updated test cases. Now have **{len(result['test_cases'])}** test cases with **{result['coverage']['percentage']:.1f}%** coverage.",
            "data": result
        }
        
    except Exception as e:
        status_placeholder.empty()
        return {
            "type": "error",
            "content": f"❌ Error: {str(e)}"
        }

def handle_exploration(url: str):
    """Handle URL exploration request"""
    
    # Create a placeholder for status updates
    status_placeholder = st.empty()
    
    try:
        # Initialize agent if not exists
        if st.session_state.exploration_agent is None:
            st.session_state.exploration_agent = ExplorationAgent()
        
        agent = st.session_state.exploration_agent
        
        # Show progress
        with status_placeholder.container():
            with st.spinner("🔍 Exploring the page..."):
                st.info("This may take a few moments. The browser will open and navigate to the URL.")
        
        # Run exploration
        exploration_data = agent.explore_url(url)
        
        # Clear status
        status_placeholder.empty()
        
        if exploration_data["status"] == "error":
            error_msg = f"❌ Exploration failed: {exploration_data.get('error', 'Unknown error')}"
            if 'phase' in exploration_data:
                error_msg += f"\n\nFailed at phase: {exploration_data['phase']}"
            return {"type": "error", "content": error_msg}
        
        # Store in session state
        st.session_state.exploration_data = exploration_data
        st.session_state.current_phase = "exploration_complete"
        
        # Save results to phase1 directory
        saved_files = agent.save_results()
        if saved_files and "error" not in saved_files:
            st.session_state.phase1_files = saved_files
        
        # Return success message
        return {
            "type": "success",
            "content": f"✅ Successfully explored: **{url}**\n\nFound **{exploration_data['metrics']['elements_found']}** interactive elements.",
            "data": exploration_data
        }
        
    except Exception as e:
        status_placeholder.empty()
        return {
            "type": "error",
            "content": f"❌ Error during exploration: {str(e)}"
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
        
        # Current Phase Indicator
        if st.session_state.current_phase:
            phase_display = st.session_state.current_phase.replace('_', ' ').title()
            st.success(f"📍 Current Phase: {phase_display}")
        else:
            st.info("📍 Current Phase: Ready")
        
        st.divider()
        
        # Quick Stats]
        if st.session_state.current_phase == "exploration_complete":
            data = st.session_state.exploration_data
            metrics = data.get("metrics", {})
            st.session_state.llm_tokens = metrics.get("llm_tokens", 0)
            st.session_state.total_time = metrics.get("total_time", 0.0)

        elif st.session_state.current_phase == "design_complete":
            data = st.session_state.design_data
            metrics = data.get("metrics", {})
            st.session_state.llm_tokens += metrics.get("llm_tokens", 0)
            st.session_state.total_time += metrics.get("total_time", 0.0)

        st.markdown("### Stats")
        st.metric("LLM Tokens", f"{st.session_state.llm_tokens}")
        st.metric("Total Time", f"{st.session_state.total_time:.2f}s")
        
        st.divider()
        
        # Reset button
        if st.button("🔄 Reset Agent", use_container_width=True, width='stretch'):
            # Cleanup agent if exists
            if st.session_state.exploration_agent:
                try:
                    st.session_state.exploration_agent.cleanup()
                except:
                    pass
            
            # Clear saved results from all phases
            ExplorationAgent.clear_results()
            DesignAgent.clear_results()
            
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.success("🗑️ Agent reset and all results cleared!")
            st.rerun()
        
        st.divider()
    
    # Main content area
    tab1, tab2 = st.tabs(["🧠 Explore", "🧪 Design"])
    
    with tab1:
        st.markdown("### Exploration & Knowledge Acquisition")
        st.markdown("Enter a URL to explore and analyze the web page structure.")
        
        # Chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display exploration results if present
                if message.get("exploration_data"):
                    display_exploration_results(message["exploration_data"])
        
        # Chat input
        if prompt := st.chat_input("Enter a URL to explore..."):
            # Add user message to session state
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Check if input is a URL
            if is_url(prompt):
                # Handle exploration
                result = handle_exploration(prompt)
                
                # Add assistant response
                assistant_msg = {
                    "role": "assistant",
                    "content": result["content"]
                }
                
                if result["type"] == "success":
                    assistant_msg["exploration_data"] = result["data"]
                
                st.session_state.messages.append(assistant_msg)
            else:
                # Handle other queries
                response = "🤔 I can help you explore web pages! Please provide a valid URL starting with http:// or https://\n\n"
                response += "**Example:** https://example.com\n\n"
                response += "More features coming soon!"
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
            
            # Rerun to display the updated messages
            st.rerun()
    
    with tab2:
        st.markdown("### Collaborative Test Design")
        st.markdown("Review and refine AI-generated test cases to achieve optimal coverage.")
        
        # Check if exploration results exist in saved files
        exploration_data = ExplorationAgent.load_results()
        if not exploration_data:
            st.warning("⚠️ Please explore a URL first in the **Explore** tab and ensure results are saved.")
        else:
            # Generate test cases button
            if not st.session_state.design_data:
                if st.button("🚀 Generate Test Cases", type="primary", use_container_width=True):
                    result = handle_test_generation()
                    st.session_state.design_messages.append({
                        "role": "assistant",
                        "content": result["content"],
                        "data": result.get("data")
                    })
                    st.rerun()
            
            # Display design results
            if st.session_state.design_data:
                display_design_results(st.session_state.design_data)
                
                st.divider()
                
                # Refinement section
                st.markdown("#### 💬 Refine Test Cases")
                st.markdown("Provide feedback to add, remove, or modify test cases.")
                
                # Show design conversation
                for msg in st.session_state.design_messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                # Refinement input
                if refinement_input := st.chat_input("Enter your feedback (e.g., 'add test for logout', 'remove TC003')..."):
                    # Add user message
                    st.session_state.design_messages.append({
                        "role": "user",
                        "content": refinement_input
                    })
                    
                    # Process refinement
                    result = handle_test_refinement(refinement_input)
                    st.session_state.design_messages.append({
                        "role": "assistant",
                        "content": result["content"]
                    })
                    st.rerun()

if __name__ == "__main__":
    main()