from typing import Dict, Any, List, Optional
from utils.gemini_client import GeminiClient
import json
import time

class DesignAgent:
    """
    Phase 2: Collaborative Test Design
    
    This agent takes exploration data and generates test case proposals.
    It works iteratively with the user to refine test coverage.
    """
    
    def __init__(self):
        self.llm = GeminiClient()
        self.test_cases = []
        self.exploration_data = None
        self.coverage_metrics = {}
        
    def generate_test_cases(self, exploration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate initial test case proposals based on exploration data.
        
        Args:
            exploration_data: The output from ExplorationAgent
            
        Returns:
            dict: Contains test_cases, coverage metrics, and LLM metrics
        """
        print("🧪 Generating test cases from exploration data...")
        
        self.exploration_data = exploration_data
        start_time = time.time()
        
        try:
            # Extract relevant information from exploration data
            page_info = exploration_data.get("page_info", {})
            elements = exploration_data.get("interactive_elements", [])
            ai_analysis = exploration_data.get("ai_analysis", {})
            
            # Create a structured prompt for the LLM
            prompt = self._create_test_generation_prompt(page_info, elements, ai_analysis)
            
            # Start a new chat session for test design
            system_instruction = """You are an expert QA engineer specialized in test case design.
Your goal is to generate comprehensive, practical test cases that maximize coverage while being realistic and executable.
Focus on functionality, edge cases, and user workflows.
Always respond with valid JSON only."""
            
            # Reset chat to start fresh conversation
            self.llm.reset_chat()
            
            # Start chat session
            response = self.llm.chat(
                message=prompt,
                system_instruction=system_instruction
            )
            
            if response["status"] == "error":
                return {
                    "status": "error",
                    "error": response.get("error", "Unknown error"),
                    "test_cases": [],
                    "metrics": {}
                }
            
            # Parse the LLM response
            test_cases = self._parse_test_cases(response["text"])
            
            # Enhance test cases with element mapping
            enhanced_test_cases = self._enhance_test_cases(test_cases, elements)
            
            # Calculate coverage metrics
            coverage = self._calculate_coverage(enhanced_test_cases, elements)
            
            # Store test cases
            self.test_cases = enhanced_test_cases
            self.coverage_metrics = coverage
            
            total_time = time.time() - start_time
            
            return {
                "status": "success",
                "test_cases": enhanced_test_cases,
                "coverage": coverage,
                "metrics": {
                    "total_test_cases": len(enhanced_test_cases),
                    "llm_tokens": response["total_tokens"],
                    "llm_response_time": response["response_time"],
                    "total_time": total_time,
                    "coverage_percentage": coverage.get("percentage", 0)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "test_cases": [],
                "metrics": {}
            }
    
    def _create_test_generation_prompt(self, page_info: Dict, elements: List[Dict], ai_analysis: Dict) -> str:
        """
        Create a detailed prompt for the LLM to generate test cases.
        
        The prompt includes:
        - Page context (URL, title, purpose)
        - Available interactive elements
        - AI analysis insights
        - Expected JSON format
        """
        # Create element summary (limit to avoid token overflow)
        element_summary = self._summarize_elements_for_prompt(elements)
        
        # Extract AI analysis insights
        page_purpose = ai_analysis.get("page_purpose", "Unknown")
        main_functionality = ai_analysis.get("main_functionality", [])
        user_workflows = ai_analysis.get("user_workflows", [])
        testable_areas = ai_analysis.get("testable_areas", [])
        
        prompt = f"""You are designing test cases for a web application.

**Page Information:**
- URL: {page_info.get('url', 'N/A')}
- Title: {page_info.get('title', 'N/A')}
- Purpose: {page_purpose}

**Main Functionality:**
{json.dumps(main_functionality, indent=2)}

**User Workflows:**
{json.dumps(user_workflows, indent=2)}

**Testable Areas:**
{json.dumps(testable_areas, indent=2)}

**Available Interactive Elements:**
{element_summary}

**Your Task:**
Generate a comprehensive set of test cases that cover:
1. Happy path scenarios (main user flows)
2. Negative test cases (invalid inputs, error handling)
3. Edge cases (boundary conditions)
4. UI validation (element visibility, text correctness)

For each test case, provide:
- A unique ID (TC001, TC002, etc.)
- A clear, descriptive name
- Priority (High, Medium, Low)
- Category (Functional, UI, Negative, Edge Case)
- Detailed steps (be specific about which elements to interact with)
- Expected result
- Elements used (reference element indices from the list above)

**Response Format (JSON only):**
{{
    "test_cases": [
        {{
            "id": "TC001",
            "name": "Test case name",
            "priority": "High",
            "category": "Functional",
            "steps": [
                "Step 1: Navigate to page",
                "Step 2: Click element X",
                "Step 3: Enter 'value' in element Y"
            ],
            "expected_result": "User should see success message",
            "element_indices": [0, 5, 10]
        }}
    ]
}}
"""
        
        return prompt
    
    def _summarize_elements_for_prompt(self, elements: List[Dict]) -> str:
        """
        Create a concise summary of elements for the LLM prompt.
        Avoids overwhelming the context window.
        """
        summary_lines = []
        
        for idx, elem in enumerate(elements):
            elem_type = elem.get("tag", "unknown")
            elem_text = elem.get("text", "") if elem.get("text") else ""
            elem_id = elem.get("id", "")
            elem_name = elem.get("name", "")
            
            line = f"[{idx}] {elem_type}"
            if elem_id:
                line += f" (id='{elem_id}')"
            if elem_name:
                line += f" (name='{elem_name}')"
            if elem_text:
                line += f" - '{elem_text}'"
            
            summary_lines.append(line)
        
        return "\n".join(summary_lines)
    
    def _parse_test_cases(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM's JSON response into test case objects.
        
        This method handles potential parsing errors gracefully:
        - Strips markdown code blocks if present
        - Validates JSON structure
        - Provides default values for missing fields
        """
        try:
            # Remove markdown code blocks if present
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith("```"):
                # Extract JSON from code block
                lines = cleaned_response.split("\n")
                cleaned_response = "\n".join(lines[1:-1])  # Remove first and last lines
            
            # Parse JSON
            data = json.loads(cleaned_response)
            
            # Extract test cases
            test_cases = data.get("test_cases", [])
            
            # Validate and normalize each test case
            normalized_cases = []
            for tc in test_cases:
                normalized_cases.append({
                    "id": tc.get("id", f"TC{len(normalized_cases)+1:03d}"),
                    "name": tc.get("name", "Unnamed Test"),
                    "priority": tc.get("priority", "Medium"),
                    "category": tc.get("category", "Functional"),
                    "steps": tc.get("steps", []),
                    "expected_result": tc.get("expected_result", ""),
                    "element_indices": tc.get("element_indices", []),
                    "status": "pending"  # pending, approved, rejected
                })
            
            return normalized_cases
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Raw response: {llm_response[:200]}...")
            return []
        except Exception as e:
            print(f"❌ Error parsing test cases: {e}")
            return []
    
    def _enhance_test_cases(self, test_cases: List[Dict], elements: List[Dict]) -> List[Dict]:
        """
        Enhance test cases by mapping element indices to actual element data.
        
        This creates a richer test case structure that includes:
        - Element details (tag, id, text)
        - Suggested locators
        - Element visibility status
        """
        enhanced_cases = []
        
        for tc in test_cases:
            enhanced_tc = tc.copy()
            element_details = []
            
            # Map element indices to actual elements
            for idx in tc.get("element_indices", []):
                if 0 <= idx < len(elements):
                    elem = elements[idx]
                    element_details.append({
                        "index": idx,
                        "tag": elem.get("tag", "unknown"),
                        "id": elem.get("id", ""),
                        "text": elem.get("text", "")[:50] if elem.get("text") else "",
                        "name": elem.get("name", ""),
                        "type": elem.get("type", "")
                    })
            
            enhanced_tc["elements"] = element_details
            enhanced_cases.append(enhanced_tc)
        
        return enhanced_cases
    
    def _calculate_coverage(self, test_cases: List[Dict], elements: List[Dict]) -> Dict[str, Any]:
        """
        Calculate coverage metrics to show how well tests cover the page.
        
        Coverage is calculated as:
        - Element coverage: % of interactive elements covered by at least one test
        - Category distribution: How tests are distributed across categories
        - Priority distribution: How tests are distributed across priorities
        """
        if not elements:
            return {"percentage": 0, "covered_elements": 0, "total_elements": 0}
        
        # Track which elements are covered
        covered_element_indices = set()
        category_counts = {}
        priority_counts = {}
        
        for tc in test_cases:
            # Count element coverage
            for idx in tc.get("element_indices", []):
                covered_element_indices.add(idx)
            
            # Count categories
            category = tc.get("category", "Unknown")
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Count priorities
            priority = tc.get("priority", "Medium")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Calculate percentage
        total_elements = len(elements)
        covered_elements = len(covered_element_indices)
        percentage = (covered_elements / total_elements * 100) if total_elements > 0 else 0
        
        return {
            "percentage": round(percentage, 2),
            "covered_elements": covered_elements,
            "total_elements": total_elements,
            "uncovered_elements": total_elements - covered_elements,
            "category_distribution": category_counts,
            "priority_distribution": priority_counts
        }
    
    def refine_test_cases(self, user_feedback: str) -> Dict[str, Any]:
        """
        Refine test cases based on user feedback.
        
        This method enables the iterative refinement loop:
        - User provides feedback (e.g., "add test for logout", "remove TC003")
        - LLM interprets the feedback and modifies test cases
        - Coverage is recalculated
        
        Args:
            user_feedback: Natural language feedback from the user
            
        Returns:
            dict: Updated test cases and metrics
        """
        print(f"🔄 Refining test cases based on feedback: {user_feedback}")
        
        start_time = time.time()
        
        try:
            # Create refinement prompt
            prompt = self._create_refinement_prompt(user_feedback)
            
            # Continue the chat conversation (system instruction already set in initial generation)
            response = self.llm.chat(message=prompt)
            
            if response["status"] == "error":
                return {
                    "status": "error",
                    "error": response.get("error", "Unknown error")
                }
            
            # Parse updated test cases
            updated_test_cases = self._parse_test_cases(response["text"])
            
            # Enhance with element mapping
            elements = self.exploration_data.get("interactive_elements", [])
            enhanced_test_cases = self._enhance_test_cases(updated_test_cases, elements)
            
            # Recalculate coverage
            coverage = self._calculate_coverage(enhanced_test_cases, elements)
            
            # Update stored test cases
            self.test_cases = enhanced_test_cases
            self.coverage_metrics = coverage
            
            total_time = time.time() - start_time
            
            return {
                "status": "success",
                "test_cases": enhanced_test_cases,
                "coverage": coverage,
                "metrics": {
                    "total_test_cases": len(enhanced_test_cases),
                    "llm_tokens": response["total_tokens"],
                    "llm_response_time": response["response_time"],
                    "total_time": total_time,
                    "coverage_percentage": coverage.get("percentage", 0)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _create_refinement_prompt(self, user_feedback: str) -> str:
        """
        Create a prompt for refining test cases based on user feedback.
        Chat context is maintained, so we only need to send the feedback.
        """
        prompt = f"""**User Feedback:**
"{user_feedback}"

**Your Task:**
Update the test cases based on the user's feedback. You can:
- Add new test cases if requested
- Remove test cases if requested
- Modify existing test cases (change priority, steps, etc.)
- Reorder test cases for better organization

Return the complete updated test case list in the same JSON format:
{{
    "test_cases": [...]
}}

Ensure all test cases maintain the required structure with id, name, priority, category, steps, expected_result, and element_indices."""
        
        return prompt
    
    def reset_conversation(self):
        """
        Reset the chat conversation.
        Useful when starting test design for a new page.
        """
        self.llm.reset_chat()
        self.test_cases = []
        self.exploration_data = None
        self.coverage_metrics = {}
    
    def get_test_summary(self) -> str:
        """
        Generate a human-readable summary of the test design.
        """
        if not self.test_cases:
            return "No test cases generated yet."
        
        summary = f"**Test Design Summary**\n\n"
        summary += f"Total Test Cases: {len(self.test_cases)}\n"
        summary += f"Coverage: {self.coverage_metrics.get('percentage', 0):.1f}%\n"
        summary += f"Elements Covered: {self.coverage_metrics.get('covered_elements', 0)}/{self.coverage_metrics.get('total_elements', 0)}\n\n"
        
        # Priority breakdown
        priority_dist = self.coverage_metrics.get('priority_distribution', {})
        summary += "**Priority Distribution:**\n"
        for priority, count in priority_dist.items():
            summary += f"- {priority}: {count}\n"
        
        # Category breakdown
        category_dist = self.coverage_metrics.get('category_distribution', {})
        summary += "\n**Category Distribution:**\n"
        for category, count in category_dist.items():
            summary += f"- {category}: {count}\n"
        
        return summary
