import uuid
import langfuse
import streamlit as st
from config import Config
from agents.exploration_agent import ExplorationAgent
import re
import base64
from io import BytesIO
import nest_asyncio
import asyncio
import sys
from agents.test_design_agent import TestDesignAgent
from agents.implementation_agent import ImplementationAgent
from agents.verification_agent import VerificationAgent
from utils.browser_controller import BrowserController
import pandas as pd

import uuid
from utils.trace_context import set_trace_id
from utils.langfuse_client import langfuse

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
    if 'test_design_agent' not in st.session_state:
        st.session_state.test_design_agent = None
    if 'test_plan' not in st.session_state:
        st.session_state.test_plan = None
    if 'review_feedback' not in st.session_state:
        st.session_state.review_feedback = ""
    if 'implementation_agent' not in st.session_state:
        st.session_state.implementation_agent = None
    if 'generated_test_code' not in st.session_state:
        st.session_state.generated_test_code = None
    if 'code_verification_results' not in st.session_state:
        st.session_state.code_verification_results = None
    if 'verification_agent' not in st.session_state:
        st.session_state.verification_agent = None
    if 'test_execution_results' not in st.session_state:
        st.session_state.test_execution_results = None
    if 'execution_evidence' not in st.session_state:
        st.session_state.execution_evidence = None
    if 'execution_analysis' not in st.session_state:
        st.session_state.execution_analysis = None
    if 'user_critique' not in st.session_state:
        st.session_state.user_critique = ""
    if 'refactored_code' not in st.session_state:
        st.session_state.refactored_code = None
    if "trace_id" not in st.session_state:
        st.session_state.trace_id = str(uuid.uuid4())


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
                suggested = elem.get("suggested_locators") or []
                locator = suggested[0] if len(suggested) > 0 else {}
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
            error_msg = ai_analysis['error']
            is_quota_error = ai_analysis.get("is_quota_error", False) or "429" in str(error_msg) or "quota" in str(error_msg).lower()
            
            if is_quota_error:
                st.error("❌ **API Quota Exceeded**")
                st.warning("""
                **You've reached your Gemini API quota limit during AI analysis.**
                
                **Free Tier Limits:**
                - 20 requests per day per model
                
                **What this means:**
                - Page elements were successfully extracted
                - AI analysis step failed due to quota limits
                - You can still proceed with test design using the extracted elements
                
                **Solutions:**
                1. **Wait**: The quota resets daily (usually at midnight UTC)
                2. **Upgrade**: Consider upgrading your Google AI Studio plan
                3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                
                **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                """)
                if ai_analysis.get("retry_after"):
                    st.info(f"⏱️ Suggested retry delay: {ai_analysis['retry_after']:.0f} seconds (but daily limit applies)")
            else:
                st.error(f"AI Analysis Error: {error_msg}")
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
            error_msg = exploration_data.get('error', 'Unknown error')
            
            # Check if it's a quota error
            ai_analysis = exploration_data.get("ai_analysis", {})
            is_quota_error = (
                ai_analysis.get("is_quota_error", False) or
                "429" in str(error_msg) or
                "quota" in str(error_msg).lower() or
                "rate limit" in str(error_msg).lower()
            )
            
            if is_quota_error:
                quota_content = """
❌ **API Quota Exceeded During Exploration**

**You've reached your Gemini API quota limit.**

**Free Tier Limits:**
- 20 requests per day per model

**What happened:**
The page exploration was partially successful (elements were found), but the AI analysis step failed due to quota limits.

**Solutions:**
1. **Wait**: The quota resets daily (usually at midnight UTC)
   - Retry delay: ~11 seconds (but daily limit applies)
2. **Upgrade**: Consider upgrading your Google AI Studio plan
3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit

**Note:** You can still proceed with test design using the elements found, but AI analysis will be limited.

**For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
"""
                return {"type": "error", "content": quota_content, "is_quota_error": True}
            else:
                error_content = f"❌ Exploration failed: {error_msg}"
                if 'phase' in exploration_data:
                    error_content += f"\n\nFailed at phase: {exploration_data['phase']}"
                return {"type": "error", "content": error_content}
        
        # Store in session state
        st.session_state.exploration_data = exploration_data
        st.session_state.current_phase = "exploration_complete"
        
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
  

    if "trace_id" not in st.session_state:
        st.session_state.trace_id = str(uuid.uuid4())

    set_trace_id(st.session_state.trace_id)
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
        
        # Quick Stats
        if st.session_state.exploration_data:
            st.subheader("📊 Session Stats")
            data = st.session_state.exploration_data
            st.metric("Total Tokens Used", data['metrics']['llm_tokens'])
            st.metric("Total Time", f"{data['metrics']['total_time']:.2f}s")
            st.metric("Elements Found", data['metrics']['elements_found'])
        
        st.divider()
        
        # Reset button
        if st.button("🔄 Reset Agent", use_container_width=True, width='stretch'):
            # Cleanup agents if exist
            if st.session_state.exploration_agent:
                try:
                    st.session_state.exploration_agent.cleanup()
                except:
                    pass
            
            if st.session_state.implementation_agent:
                try:
                    st.session_state.implementation_agent.cleanup()
                except:
                    pass
            
            if st.session_state.verification_agent:
                try:
                    st.session_state.verification_agent.cleanup()
                except:
                    pass
            
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.divider()
        
        # Help section
        with st.expander("ℹ️ Help"):
            st.markdown("""
            **How to use:**
            1. Enter a URL to explore a web page
            2. Review the exploration results
            3. Proceed to test design (coming soon)
            
            **Supported commands:**
            - Enter any valid URL (http:// or https://)
            - More commands coming soon!
            """)
    
    # Main content area
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Chat",
    "📊 Exploration Details",
    "🧪 Test Design",
    "🧾 Test Review & Approval",
    "💻 Code Generation",
    "✅ Verification & Evidence"
])

    
    with tab1:
        st.subheader("Chat Interface")
        
        # Chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display exploration results if present
                if message.get("exploration_data"):
                    display_exploration_results(message["exploration_data"])
        
        # Chat input
        if prompt := st.chat_input("Enter a URL to explore or ask a question..."):
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
        st.subheader("Exploration Details")
        
        if st.session_state.exploration_data:
            display_exploration_results(st.session_state.exploration_data)
        else:
            st.info("No exploration data yet. Enter a URL in the chat to get started!")

    with tab3:
        st.subheader("🧪 Test Design – AI Proposal")

        if st.session_state.current_phase != "exploration_complete" and not st.session_state.test_plan:
            st.info("Complete page exploration before designing tests.")
            st.stop()

        # Button to trigger test design
        if st.session_state.test_plan is None:
            if st.button("🧪 Generate Test Plan"):
                if st.session_state.test_design_agent is None:
                    st.session_state.test_design_agent = TestDesignAgent()

                agent = st.session_state.test_design_agent

                with st.spinner("Designing test plan..."):
                    try:
                        st.session_state.test_plan = agent.generate_test_plan(
                            st.session_state.exploration_data
                        )
                        st.session_state.current_phase = "test_design_ready"
                        st.rerun()
                    except ValueError as e:
                        error_msg = str(e)
                        st.error(f"❌ Test plan generation failed: {error_msg}")
                        st.info("💡 Tip: The LLM may have returned invalid JSON. Try again or check your API key.")
                    except RuntimeError as e:
                        error_msg = str(e)
                        # Check if it's a quota error from the agent
                        if "quota" in error_msg.lower() or "429" in error_msg:
                            st.error("❌ **API Quota Exceeded**")
                            st.warning("""
                            **You've reached your Gemini API quota limit.**
                            
                            **Free Tier Limits:**
                            - 20 requests per day per model
                            
                            **Solutions:**
                            1. **Wait**: The quota resets daily (usually at midnight UTC)
                            2. **Upgrade**: Consider upgrading your Google AI Studio plan
                            3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                            
                            **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                            """)
                        else:
                            st.error(f"❌ Test plan generation failed: {error_msg}")
                    except Exception as e:
                        error_msg = str(e)
                        # Check for quota errors in exception message
                        if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                            st.error("❌ **API Quota Exceeded**")
                            st.warning("""
                            **You've reached your Gemini API quota limit.**
                            
                            **Free Tier Limits:**
                            - 20 requests per day per model
                            
                            **Solutions:**
                            1. **Wait**: The quota resets daily (usually at midnight UTC)
                            2. **Upgrade**: Consider upgrading your Google AI Studio plan
                            3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                            
                            **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                            """)
                        else:
                            st.error(f"❌ Unexpected error: {error_msg}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())

        # Display proposed test plan
        if st.session_state.test_plan:
            plan = st.session_state.test_plan

            st.markdown("### 📋 Proposed Test Cases")

            df = pd.DataFrame([
                {
                    "ID": tc["id"],
                    "Title": tc["title"],
                    "Priority": tc["priority"],
                    "Type": tc["type"],
                    "Elements": ", ".join(map(str, tc["related_elements"]))
                }
                for tc in plan["test_cases"]
            ])

            st.dataframe(df, use_container_width=True)

            st.markdown("### 📊 Coverage Summary")
            st.json(plan["coverage_summary"])

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✏️ Request Changes"):
                    st.session_state.current_phase = "test_review"
                    st.rerun()

            with col2:
                if st.button("✅ Approve Test Plan"):
                    st.session_state.current_phase = "test_design_approved"
                    st.success("Test plan approved. You may proceed to test generation.")

    with tab4:
        st.subheader("🧾 Test Review & Approval")

        if st.session_state.current_phase not in ["test_review", "test_design_approved"]:
            st.info("No test plan is currently under review.")
            st.stop()

        plan = st.session_state.test_plan
        agent = st.session_state.test_design_agent

        st.markdown("### ✏️ Reviewer Feedback")

        st.session_state.review_feedback = st.text_area(
            "Describe what should be changed, added, or removed:",
            value=st.session_state.review_feedback,
            height=120
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔁 Refine Test Plan"):
                if not st.session_state.review_feedback.strip():
                    st.warning("Please provide feedback before refining.")
                else:
                    with st.spinner("Refining test plan..."):
                        try:
                            st.session_state.test_plan = agent.refine_test_plan(
                                existing_plan=plan,
                                reviewer_feedback=st.session_state.review_feedback
                            )
                            st.session_state.review_feedback = ""
                            st.session_state.current_phase = "test_design_ready"
                            st.success("Test plan refined.")
                            st.rerun()
                        except ValueError as e:
                            error_msg = str(e)
                            st.error(f"❌ Test plan refinement failed: {error_msg}")
                            st.info("💡 Tip: The LLM may have returned invalid JSON. Try again with different feedback.")
                        except RuntimeError as e:
                            error_msg = str(e)
                            if "quota" in error_msg.lower() or "429" in error_msg:
                                st.error("❌ **API Quota Exceeded**")
                                st.warning("""
                                **You've reached your Gemini API quota limit.**
                                
                                **Free Tier Limits:**
                                - 20 requests per day per model
                                
                                **Solutions:**
                                1. **Wait**: The quota resets daily (usually at midnight UTC)
                                2. **Upgrade**: Consider upgrading your Google AI Studio plan
                                3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                                
                                **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                                """)
                            else:
                                st.error(f"❌ Test plan refinement failed: {error_msg}")
                        except Exception as e:
                            error_msg = str(e)
                            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                                st.error("❌ **API Quota Exceeded**")
                                st.warning("""
                                **You've reached your Gemini API quota limit.**
                                
                                **Free Tier Limits:**
                                - 20 requests per day per model
                                
                                **Solutions:**
                                1. **Wait**: The quota resets daily (usually at midnight UTC)
                                2. **Upgrade**: Consider upgrading your Google AI Studio plan
                                3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                                
                                **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                                """)
                            else:
                                st.error(f"❌ Unexpected error: {error_msg}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())

        with col2:
            if st.session_state.current_phase == "test_design_approved":
                st.success("✅ Test plan approved.")
                st.markdown("You may proceed to **test creation**.")

    with tab5:
        st.subheader("💻 Code Generation")
        
        # Wrap everything in try-except to catch any errors
        try:
            # Always show debug info to help diagnose issues
            with st.expander("🔍 Debug Information", expanded=True):
                st.write(f"**Current Phase:** {st.session_state.current_phase}")
                st.write(f"**Test Plan Exists:** {st.session_state.test_plan is not None}")
                st.write(f"**Generated Code Exists:** {st.session_state.generated_test_code is not None}")
                st.write(f"**Exploration Data Exists:** {st.session_state.exploration_data is not None}")
                if st.session_state.test_plan:
                    st.write(f"**Test Cases Count:** {len(st.session_state.test_plan.get('test_cases', []))}")
                if st.session_state.generated_test_code:
                    st.write(f"**Code Status:** {st.session_state.generated_test_code.get('status', 'unknown')}")
            
            # Check prerequisites
            if st.session_state.current_phase != "test_design_approved" and not st.session_state.generated_test_code:
                st.info("⚠️ Please complete and approve the test plan before generating code.")
                if st.session_state.test_plan:
                    st.warning("Test plan exists but not approved. Please approve it in the 'Test Review & Approval' tab.")
                    st.markdown("**To proceed:**")
                    st.markdown("1. Go to the **🧾 Test Review & Approval** tab")
                    st.markdown("2. Click **✅ Approve Test Plan** button")
                    st.markdown("3. Return to this tab to generate code")
                else:
                    st.error("No test plan found. Please complete Test Design first.")
                st.stop()
            
            if not st.session_state.test_plan:
                st.error("No test plan available. Please complete Test Design first.")
                st.markdown("**Steps to complete:**")
                st.markdown("1. Go to **🧪 Test Design** tab")
                st.markdown("2. Click **🧪 Generate Test Plan**")
                st.markdown("3. Go to **🧾 Test Review & Approval** tab")
                st.markdown("4. Click **✅ Approve Test Plan**")
                st.markdown("5. Return here to generate code")
                st.stop()
            
            # Debug: Check if phase says code_generated but code is missing
            if st.session_state.current_phase == "code_generated" and not st.session_state.generated_test_code:
                st.warning("⚠️ Code generation state was lost. Please regenerate the code.")
                st.info("This can happen if the page was refreshed. Click the button below to regenerate.")
                st.session_state.current_phase = "test_design_approved"  # Reset to allow regeneration
            
            # Initialize implementation agent
            if st.session_state.implementation_agent is None:
                # Reuse browser from exploration agent if available
                browser = None
                if st.session_state.exploration_agent:
                    browser = st.session_state.exploration_agent.browser
                
                # If no browser, create a new one
                if browser is None:
                    browser = BrowserController()
                    browser.launch()
                
                st.session_state.implementation_agent = ImplementationAgent(browser=browser)
            
            # Code generation section
            st.markdown("### 🔧 Generate Test Code")
            
            # Debug information (can be removed later)
            if Config.DEBUG_MODE:
                with st.expander("🔍 Debug Info"):
                    st.write(f"Current Phase: {st.session_state.current_phase}")
                    st.write(f"Generated Code Exists: {st.session_state.generated_test_code is not None}")
                    st.write(f"Test Plan Exists: {st.session_state.test_plan is not None}")
                    if st.session_state.generated_test_code:
                        st.write(f"Code Status: {st.session_state.generated_test_code.get('status', 'unknown')}")
            
            if st.session_state.generated_test_code is None:
                test_plan = st.session_state.test_plan
                
                # Test case selection
                st.markdown("**Select test cases to generate:**")
                test_cases = test_plan.get("test_cases", [])
                
                if not test_cases:
                    st.error("No test cases in the test plan.")
                    st.stop()
                
                # Create checkboxes for test case selection
                selected_test_ids = []
                for tc in test_cases:
                    if st.checkbox(
                        f"{tc.get('id')}: {tc.get('title')}",
                        value=True,
                        key=f"select_{tc.get('id')}"
                    ):
                        selected_test_ids.append(tc.get('id'))
                
                if not selected_test_ids:
                    st.warning("Please select at least one test case to generate.")
                    st.stop()
                
                # Generate button
                if st.button("🚀 Generate Test Code", type="primary", use_container_width=True):
                    with st.spinner("Generating test code with intelligent locator selection and self-correction..."):
                        try:
                            result = st.session_state.implementation_agent.generate_test_code(
                                test_plan=test_plan,
                                exploration_data=st.session_state.exploration_data,
                                test_case_ids=selected_test_ids
                            )
                            
                            if result["status"] == "success":
                                st.session_state.generated_test_code = result
                                st.session_state.code_verification_results = result.get("verification_results", [])
                                st.session_state.current_phase = "code_generated"
                                st.success("✅ Test code generated successfully!")
                                st.rerun()
                            else:
                                error_msg = result.get('error', 'Unknown error')
                                if "429" in str(error_msg) or "quota" in str(error_msg).lower():
                                    st.error("❌ **API Quota Exceeded**")
                                    st.warning("""
                                    **You've reached your Gemini API quota limit.**
                                    
                                    **Free Tier Limits:**
                                    - 20 requests per day per model
                                    
                                    **Solutions:**
                                    1. **Wait**: The quota resets daily (usually at midnight UTC)
                                    2. **Upgrade**: Consider upgrading your Google AI Studio plan
                                    3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                                    
                                    **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                                    """)
                                else:
                                    st.error(f"❌ Code generation failed: {error_msg}")
                        except Exception as e:
                            error_msg = str(e)
                            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                                st.error("❌ **API Quota Exceeded**")
                                st.warning("""
                                **You've reached your Gemini API quota limit.**
                                
                                **Free Tier Limits:**
                                - 20 requests per day per model
                                
                                **Solutions:**
                                1. **Wait**: The quota resets daily (usually at midnight UTC)
                                2. **Upgrade**: Consider upgrading your Google AI Studio plan
                                3. **Check Usage**: Visit https://ai.dev/usage?tab=rate-limit
                                
                                **For more info**: https://ai.google.dev/gemini-api/docs/rate-limits
                                """)
                            else:
                                st.error(f"❌ Error during code generation: {error_msg}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
            
            # Display generated code
            if st.session_state.generated_test_code:
                try:
                    result = st.session_state.generated_test_code
                    
                    # Validate result structure
                    if not isinstance(result, dict):
                        st.error("❌ Invalid code data structure. Please regenerate.")
                        st.session_state.generated_test_code = None
                        st.rerun()
                        st.stop()
                    
                    if result.get("status") != "success":
                        st.error(f"❌ Code generation failed: {result.get('error', 'Unknown error')}")
                        st.session_state.generated_test_code = None
                        st.rerun()
                        st.stop()
                    
                    # Metrics
                    st.markdown("### 📊 Generation Metrics")
                    metrics = result.get("metrics", {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Tests Generated", metrics.get("tests_generated", 0))
                    with col2:
                        st.metric("Total Tokens", metrics.get("total_tokens", 0))
                    with col3:
                        st.metric("Verification Passed", metrics.get("verification_passed", 0))
                    with col4:
                        st.metric("Verification Failed", metrics.get("verification_failed", 0))
                    
                    st.divider()
                    
                    # Verification results
                    if st.session_state.code_verification_results:
                        st.markdown("### ✅ Verification Results")
                        
                        for verification in st.session_state.code_verification_results:
                            test_id = verification.get("test_id", "Unknown")
                            status = verification.get("status", "unknown")
                            
                            if status == "success":
                                st.success(f"✅ {test_id}: Code verified successfully")
                            elif status == "partial":
                                st.warning(f"⚠️ {test_id}: Code generated with some issues")
                                if verification.get("verification"):
                                    issues = verification["verification"].get("issues", [])
                                    for issue in issues:
                                        st.write(f"  - {issue}")
                            elif status == "error":
                                st.error(f"❌ {test_id}: Code generation failed")
                                if verification.get("error"):
                                    st.write(f"  Error: {verification['error']}")
                            elif status == "skipped":
                                st.info(f"ℹ️ {test_id}: Verification skipped")
                        
                        st.divider()
                    
                    # Generated code display
                    st.markdown("### 📝 Generated Test Code")
                    
                    # Code download option
                    code_text = result.get("test_code", "")
                    
                    if not code_text or code_text.strip() == "":
                        st.error("❌ No code was generated. The test_code field is empty.")
                        st.info("Please try regenerating the code.")
                    else:
                        st.download_button(
                            label="📥 Download Test Code",
                            data=code_text,
                            file_name="generated_tests.py",
                            mime="text/x-python",
                            use_container_width=True
                        )
                        
                        # Code editor/viewer
                        st.code(code_text, language="python")
                    
                    # Individual test breakdown
                    if result.get("individual_tests"):
                        st.markdown("### 📋 Individual Test Breakdown")
                        
                        for idx, test in enumerate(result["individual_tests"], 1):
                            # Handle both dict and string formats
                            if isinstance(test, str):
                                # If test is a string, treat it as code
                                with st.expander(f"Test {idx}: Generated Test"):
                                    st.code(test, language="python")
                            elif isinstance(test, dict):
                                # If test is a dict, extract info
                                test_id = test.get('test_id', f'Test_{idx}')
                                test_code = test.get("test_code", "")
                                with st.expander(f"Test {idx}: {test_id}"):
                                    if test_code:
                                        st.code(test_code, language="python")
                                    else:
                                        st.warning("No test code available")
                                    
                                    # Test metadata
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("Tokens", test.get("tokens", 0))
                                    with col2:
                                        st.metric("Generation Time", f"{test.get('generation_time', 0):.2f}s")
                            else:
                                st.warning(f"Unknown test format: {type(test)}")
                    
                    # Regenerate option
                    st.divider()
                    if st.button("🔄 Regenerate Code", use_container_width=True):
                        st.session_state.generated_test_code = None
                        st.session_state.code_verification_results = None
                        st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error displaying generated code: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
                    st.info("💡 Try clicking '🔄 Regenerate Code' to fix this issue.")
                    # Show what we have in session state for debugging
                    with st.expander("Debug: Session State"):
                        st.write(f"Generated Code Type: {type(st.session_state.generated_test_code)}")
                        if st.session_state.generated_test_code:
                            st.write(f"Keys: {list(st.session_state.generated_test_code.keys()) if isinstance(st.session_state.generated_test_code, dict) else 'Not a dict'}")
        
        except Exception as e:
            # Catch any errors that happen in the entire tab
            st.error("❌ **Critical Error in Code Generation Tab**")
            st.error(f"**Error Message:** {str(e)}")
            import traceback
            with st.expander("🔍 Full Error Details (Click to Expand)", expanded=True):
                st.code(traceback.format_exc())
            
            st.markdown("---")
            st.markdown("### 🔧 Troubleshooting Steps:")
            st.markdown("1. **Check the error details above**")
            st.markdown("2. **Try resetting**: Click '🔄 Reset Agent' in the sidebar")
            st.markdown("3. **Check prerequisites**: Ensure test plan is approved")
            st.markdown("4. **Refresh the page** (F5) and try again")
            
            # Show current state
            st.markdown("### 📊 Current State:")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Phase:** {st.session_state.get('current_phase', 'None')}")
            with col2:
                st.write(f"**Test Plan:** {'✅' if st.session_state.get('test_plan') else '❌'}")
            with col3:
                st.write(f"**Generated Code:** {'✅' if st.session_state.get('generated_test_code') else '❌'}")
            
            # Show debug info
            with st.expander("🔍 Debug Information", expanded=True):
                st.write(f"**Current Phase:** {st.session_state.get('current_phase', 'None')}")
                st.write(f"**Test Plan Exists:** {st.session_state.get('test_plan') is not None}")
                st.write(f"**Generated Code Exists:** {st.session_state.get('generated_test_code') is not None}")
                st.write(f"**Exploration Data Exists:** {st.session_state.get('exploration_data') is not None}")

    with tab6:
        st.subheader("✅ Verification & Evidence")
        
        try:
            # Check prerequisites
            if not st.session_state.generated_test_code:
                st.info("⚠️ Please complete Code Generation before verifying tests.")
                st.markdown("**To proceed:**")
                st.markdown("1. Go to **💻 Code Generation** tab")
                st.markdown("2. Generate test code")
                st.markdown("3. Return here to execute and verify")
                st.stop()
            
            # Initialize verification agent
            if st.session_state.verification_agent is None:
                browser = None
                if st.session_state.exploration_agent:
                    browser = st.session_state.exploration_agent.browser
                if browser is None and st.session_state.implementation_agent:
                    browser = st.session_state.implementation_agent.browser
                
                st.session_state.verification_agent = VerificationAgent(browser=browser)
            
            # Execution section
            st.markdown("### 🚀 Test Execution")
            
            if st.session_state.test_execution_results is None:
                generated_code = st.session_state.generated_test_code
                
                # Test selection
                individual_tests = generated_code.get("individual_tests", [])
                if individual_tests:
                    st.markdown("**Select tests to execute:**")
                    selected_test_ids = []
                    for idx, test in enumerate(individual_tests):
                        # Handle both dict and string formats
                        if isinstance(test, dict):
                            test_id = test.get("test_id", f"test_{idx}")
                            test_label = test_id
                        elif isinstance(test, str):
                            test_id = f"test_{idx}"
                            test_label = f"Test {idx + 1}"
                        else:
                            test_id = f"test_{idx}"
                            test_label = f"Test {idx + 1}"
                        
                        if st.checkbox(
                            test_label,
                            value=True,
                            key=f"execute_{test_id}_{idx}"
                        ):
                            selected_test_ids.append(test_id)
                else:
                    selected_test_ids = None
                    st.info("Will execute all generated tests")
                
                # Execute button
                if st.button("▶️ Execute Tests", type="primary", use_container_width=True):
                    with st.spinner("Executing tests and collecting evidence (screenshots, logs)..."):
                        try:
                            result = st.session_state.verification_agent.execute_tests(
                                generated_code=generated_code,
                                test_case_ids=selected_test_ids
                            )
                            
                            if result["status"] == "success":
                                st.session_state.test_execution_results = result
                                st.session_state.execution_evidence = result.get("evidence", {})
                                st.session_state.current_phase = "verification_complete"
                                st.success("✅ Test execution completed!")
                                st.rerun()
                            else:
                                st.error(f"❌ Test execution failed: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Error during test execution: {str(e)}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
            
            # Display execution results
            if st.session_state.test_execution_results:
                results = st.session_state.test_execution_results
                summary = results.get("summary", {})
                
                # Execution summary
                st.markdown("### 📊 Execution Summary")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Tests Executed", summary.get("tests_executed", 0))
                with col2:
                    st.metric("Tests Passed", summary.get("tests_passed", 0), 
                             delta=f"{summary.get('tests_failed', 0)} failed" if summary.get('tests_failed', 0) > 0 else None)
                with col3:
                    st.metric("Tests Failed", summary.get("tests_failed", 0))
                with col4:
                    st.metric("Execution Time", f"{summary.get('total_execution_time', 0):.2f}s")
                with col5:
                    st.metric("Screenshots", summary.get("screenshots_count", 0))
                
                st.divider()
                
                # Evidence display
                st.markdown("### 📸 Evidence Collection")
                
                evidence = st.session_state.execution_evidence or {}
                screenshots = evidence.get("screenshots", [])
                logs = evidence.get("logs", [])
                report = evidence.get("report", {})
                
                # Screenshots gallery
                if screenshots:
                    st.markdown("#### 📷 Screenshots")
                    # Display screenshots in columns
                    cols_per_row = 3
                    for i in range(0, len(screenshots), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j, screenshot in enumerate(screenshots[i:i+cols_per_row]):
                            with cols[j]:
                                try:
                                    screenshot_b64 = screenshot.get("base64", "")
                                    if screenshot_b64:
                                        st.image(
                                            f"data:image/png;base64,{screenshot_b64}",
                                            caption=screenshot.get("name", "Screenshot"),
                                            use_container_width=True
                                        )
                                    else:
                                        st.info(f"Screenshot: {screenshot.get('name', 'Unknown')}")
                                except Exception as e:
                                    st.warning(f"Could not display screenshot: {screenshot.get('name', 'Unknown')}")
                    
                    st.divider()
                
                # Execution log
                if logs:
                    st.markdown("#### 📝 Execution Log")
                    with st.expander("View Detailed Execution Log", expanded=False):
                        for log_entry in logs:
                            step = log_entry.get("step", "Unknown")
                            details = log_entry.get("details", {})
                            timestamp = log_entry.get("timestamp", 0)
                            
                            st.write(f"**{step}** (t={timestamp:.2f}s)")
                            if details:
                                st.json(details)
                            st.divider()
                
                # Test details
                execution_results = results.get("execution_results", [])
                if execution_results:
                    st.markdown("#### 📋 Test Details")
                    for result in execution_results:
                        test_id = result.get("test_id", "Unknown")
                        status = result.get("status", "unknown")
                        
                        with st.expander(f"{test_id} - {status.upper()}", expanded=status != "success"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Status", status.upper())
                                st.metric("Execution Time", f"{result.get('execution_time', 0):.2f}s")
                            with col2:
                                st.metric("Screenshots", len(result.get("screenshots", [])))
                                st.metric("Log Entries", len(result.get("execution_log", [])))
                            
                            # Errors
                            errors = result.get("errors", [])
                            if errors:
                                st.error("**Errors:**")
                                for error in errors:
                                    st.code(error, language="text")
                            
                            # Warnings
                            warnings = result.get("warnings", [])
                            if warnings:
                                st.warning("**Warnings:**")
                                for warning in warnings:
                                    st.write(f"- {warning}")
                            
                            # Test-specific screenshots
                            test_screenshots = result.get("screenshots", [])
                            if test_screenshots:
                                st.markdown("**Screenshots:**")
                                for screenshot in test_screenshots:
                                    try:
                                        screenshot_b64 = screenshot.get("base64", "")
                                        if screenshot_b64:
                                            st.image(
                                                f"data:image/png;base64,{screenshot_b64}",
                                                caption=screenshot.get("name", "Screenshot"),
                                                use_container_width=True
                                            )
                                    except:
                                        pass
                
                st.divider()
                
                # Analysis and Review section
                st.markdown("### 🔍 Analysis & Review")
                
                # Get AI analysis if not already done
                if st.session_state.execution_analysis is None:
                    if st.button("🤖 Analyze Execution Results", use_container_width=True):
                        with st.spinner("Analyzing execution results..."):
                            try:
                                analysis = st.session_state.verification_agent.analyze_execution_results(
                                    execution_results=results
                                )
                                
                                if analysis["status"] == "success":
                                    st.session_state.execution_analysis = analysis.get("analysis", {})
                                    st.success("✅ Analysis complete!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Analysis failed: {analysis.get('error', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"❌ Error during analysis: {str(e)}")
                
                # Display analysis
                if st.session_state.execution_analysis:
                    analysis = st.session_state.execution_analysis
                    
                    # Trust score
                    trust_score = analysis.get("trust_score", 0)
                    st.markdown("#### 🎯 Trust Score")
                    st.progress(trust_score / 100)
                    st.metric("Trust Score", f"{trust_score}/100")
                    
                    # Overall assessment
                    st.markdown("#### 📊 Overall Assessment")
                    st.info(analysis.get("overall_assessment", "No assessment available"))
                    
                    # Strengths
                    strengths = analysis.get("strengths", [])
                    if strengths:
                        st.markdown("#### ✅ Strengths")
                        for strength in strengths:
                            st.success(f"• {strength}")
                    
                    # Issues
                    issues = analysis.get("issues_found", [])
                    if issues:
                        st.markdown("#### ⚠️ Issues Found")
                        for issue in issues:
                            severity = issue.get("severity", "Medium")
                            severity_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(severity, "🟡")
                            st.write(f"{severity_color} **{issue.get('issue', 'Unknown')}** ({severity})")
                            st.write(f"   💡 {issue.get('recommendation', 'No recommendation')}")
                    
                    # Recommendations
                    recommendations = analysis.get("recommendations", [])
                    if recommendations:
                        st.markdown("#### 💡 Recommendations")
                        for rec in recommendations:
                            st.write(f"• {rec}")
                
                st.divider()
                
                # User Critique and Refactoring
                st.markdown("### ✏️ Review & Refactoring")
                
                st.markdown("**Provide your critique or feedback:**")
                user_critique = st.text_area(
                    "What should be improved? What didn't work as expected?",
                    value=st.session_state.user_critique,
                    height=120,
                    key="critique_input"
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🔁 Refactor Based on Critique", use_container_width=True):
                        if not user_critique.strip():
                            st.warning("Please provide critique before refactoring.")
                        else:
                            with st.spinner("Refactoring test code based on your feedback..."):
                                try:
                                    generated_code = st.session_state.generated_test_code
                                    test_code = generated_code.get("test_code", "")
                                    
                                    refactored = st.session_state.verification_agent.refactor_test_code(
                                        original_code=test_code,
                                        critique=user_critique,
                                        execution_results=results
                                    )
                                    
                                    if refactored["status"] == "success":
                                        st.session_state.refactored_code = refactored
                                        st.session_state.user_critique = user_critique
                                        st.success("✅ Code refactored successfully!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Refactoring failed: {refactored.get('error', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"❌ Error during refactoring: {str(e)}")
                                    import traceback
                                    with st.expander("Error Details"):
                                        st.code(traceback.format_exc())
                
                with col2:
                    if st.button("🔄 Re-execute Tests", use_container_width=True):
                        st.session_state.test_execution_results = None
                        st.session_state.execution_evidence = None
                        st.session_state.execution_analysis = None
                        st.rerun()
                
                # Display refactored code
                if st.session_state.refactored_code:
                    refactored = st.session_state.refactored_code
                    
                    st.markdown("#### 🔧 Refactored Code")
                    
                    # Changes made
                    changes = refactored.get("changes_made", [])
                    if changes:
                        st.markdown("**Changes Made:**")
                        for change in changes:
                            st.write(f"• {change}")
                    
                    # Explanation
                    explanation = refactored.get("explanation", "")
                    if explanation:
                        st.info(explanation)
                    
                    # Refactored code
                    refactored_code = refactored.get("refactored_code", "")
                    if refactored_code:
                        st.code(refactored_code, language="python")
                        
                        # Download refactored code
                        st.download_button(
                            label="📥 Download Refactored Code",
                            data=refactored_code,
                            file_name="refactored_tests.py",
                            mime="text/x-python",
                            use_container_width=True
                        )
                        
                        # Option to use refactored code
                        if st.button("✅ Use Refactored Code", use_container_width=True):
                            # Update generated code with refactored version
                            generated_code = st.session_state.generated_test_code.copy()
                            generated_code["test_code"] = refactored_code
                            st.session_state.generated_test_code = generated_code
                            st.session_state.refactored_code = None
                            st.session_state.test_execution_results = None
                            st.success("✅ Refactored code applied! You can now re-execute tests.")
                            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Critical Error in Verification Tab: {str(e)}")
            import traceback
            with st.expander("🔍 Full Error Details", expanded=True):
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()