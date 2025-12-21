"""
Phase 3: Implementation (Code Generation) Agent

Generates executable, clean, and maintainable test code using Playwright + Python.
Features:
- Intelligent locator strategy selection
- Self-correction mechanisms
- Code verification and validation
"""

from typing import Dict, Any, List, Optional
import json
import time
import re
from utils.gemini_client import GeminiClient
from utils.browser_controller import BrowserController
from utils.locator_strategy import resolve_element_locator, LocatorSelector
from utils.code_verifier import CodeVerifier, auto_correct_locator
from utils.json_parser import extract_json_from_text
from utils.langfuse_client import langfuse
from utils.trace_context import get_trace_id


class ImplementationAgent:
    """
    Phase 3: Implementation Agent
    
    Converts approved test plans into executable Playwright + Python test code.
    Implements intelligent locator selection and self-correction.
    """
    
    def __init__(self, browser: Optional[BrowserController] = None):
        self.llm = GeminiClient()
        self.browser = browser
        self.verifier = CodeVerifier(browser) if browser else None
        self.generated_tests = []
    
    def generate_test_code(
        self,
        test_plan: Dict[str, Any],
        exploration_data: Dict[str, Any],
        test_case_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate executable test code for test cases.
        
        Args:
            test_plan: Approved test plan from Phase 2
            exploration_data: Exploration data from Phase 1
            test_case_ids: Optional list of specific test case IDs to generate
            
        Returns:
            dict: Generated test code with verification results
        """
        print("🔧 Starting test code generation...")
        trace_id = get_trace_id()

        with langfuse.start_as_current_observation(
            as_type="span",
            name="phase.code_generation",
            
            input={"requested_test_case_ids": test_case_ids}
        ):
            # ENTIRE generate_test_code LOGIC

            # Filter test cases if specific IDs provided
            test_cases = test_plan.get("test_cases", [])
            if test_case_ids:
                test_cases = [tc for tc in test_cases if tc.get("id") in test_case_ids]
            
            if not test_cases:
              
                return {
                    "status": "error",
                    "error": "No test cases to generate code for"
                }
            
            generated_tests = []
            total_tokens = 0
            total_time = 0
            verification_results = []
            
            for test_case in test_cases:
                print(f"  Generating code for: {test_case.get('id', 'Unknown')}")
                
                # Generate code for this test case
                result = self._generate_single_test_code(
                    test_case=test_case,
                    exploration_data=exploration_data,
                    page_url=test_plan.get("page_url", exploration_data.get("url", ""))
                )
                
                if result["status"] == "success":
                    generated_tests.append(result["test_code"])
                    total_tokens += result.get("tokens", 0)
                    total_time += result.get("generation_time", 0)
                    
                    # Verify the generated code
                    if self.verifier:
                        verification = self._verify_and_correct_code(
                            test_code=result["test_code"],
                            test_case=test_case,
                            exploration_data=exploration_data,
                            page_url=test_plan.get("page_url", "")
                        )
                        verification_results.append(verification)
                    else:
                        verification_results.append({
                            "test_id": test_case.get("id"),
                            "status": "skipped",
                            "reason": "Browser not available for verification"
                        })
                else:
                    verification_results.append({
                        "test_id": test_case.get("id"),
                        "status": "error",
                        "error": result.get("error", "Code generation failed")
                    })
           

            return {
                "status": "success",
                "test_code": self._combine_test_code(generated_tests),
                "individual_tests": generated_tests,
                "verification_results": verification_results,
                "metrics": {
                    "tests_generated": len(generated_tests),
                    "total_tokens": total_tokens,
                    "total_time": total_time,
                    "verification_passed": sum(1 for v in verification_results if v.get("status") == "success"),
                    "verification_failed": sum(1 for v in verification_results if v.get("status") == "error")
                }
            }
        
    def _generate_single_test_code(
        self,
        test_case: Dict[str, Any],
        exploration_data: Dict[str, Any],
        page_url: str
    ) -> Dict[str, Any]:
        """
        Generate code for a single test case.
        
        Args:
            test_case: Test case dictionary
            exploration_data: Exploration data
            page_url: URL of the page under test
            
        Returns:
            dict: Generated test code and metadata
        """
        start_time = time.time()
        
        # Resolve locators for related elements
        element_locators = self._resolve_element_locators(
            test_case.get("related_elements", []),
            exploration_data
        )
        
        # Build prompt for code generation
        prompt = self._build_code_generation_prompt(
            test_case=test_case,
            element_locators=element_locators,
            page_url=page_url,
            exploration_data=exploration_data
        )
        
        # Generate code using LLM
        response = self.llm.generate_structured(
            prompt=prompt,
            system_instruction=(
                "You are an expert test automation engineer writing Playwright + Python tests. "
                "Generate clean, maintainable, and executable test code. "
                "Use the provided locators and follow Playwright best practices."
            )
        )
        
        generation_time = time.time() - start_time
        
        if response.get("status") != "success":
            return {
                "status": "error",
                "error": response.get("error", "Code generation failed"),
                "generation_time": generation_time
            }
        
        # Extract code from response
        # Try to parse as JSON first (if LLM returns structured)
        code_data = extract_json_from_text(response["text"])
        if code_data and isinstance(code_data, dict) and "test_code" in code_data:
            test_code = code_data.get("test_code", response["text"])
        else:
            # If not JSON, assume raw code
            test_code = response["text"]
            # Clean up markdown code blocks if present
            test_code = self._clean_code_blocks(test_code)
        
        return {
            "status": "success",
            "test_code": test_code,
            "test_id": test_case.get("id"),
            "tokens": response.get("total_tokens", 0),
            "generation_time": generation_time
        }
    
    def _resolve_element_locators(
        self,
        element_indices: List[int],
        exploration_data: Dict[str, Any]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Resolve locators for all elements referenced in test case.
        
        Args:
            element_indices: List of element indices from exploration
            exploration_data: Full exploration data
            
        Returns:
            dict: Mapping of element index to locator information
        """
        locators = {}
        
        for idx in element_indices:
            locator_info = resolve_element_locator(idx, exploration_data)
            locators[idx] = {
                "locator": locator_info,
                "playwright_code": LocatorSelector.get_playwright_locator_code(locator_info)
            }
        
        return locators
    
    def _build_code_generation_prompt(
        self,
        test_case: Dict[str, Any],
        element_locators: Dict[int, Dict[str, Any]],
        page_url: str,
        exploration_data: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM code generation"""
        
        # Format element locators for prompt
        locator_info = []
        for idx, loc_data in element_locators.items():
            element = exploration_data["interactive_elements"][idx] if idx < len(exploration_data["interactive_elements"]) else {}
            locator_info.append({
                "element_index": idx,
                "tag": element.get("tag", "unknown"),
                "text": (element.get("text") or "")[:50],
                "id": element.get("id"),
                "best_locator": loc_data["playwright_code"],
                "strategy": loc_data["locator"].get("strategy"),
                "confidence": loc_data["locator"].get("confidence", "medium")
            })
        
        prompt = f"""
Generate executable Playwright + Python test code for the following test case.

TEST CASE:
{json.dumps(test_case, indent=2)}

PAGE URL:
{page_url}

ELEMENT LOCATORS:
{json.dumps(locator_info, indent=2)}

IMPORTANT: This test will be executed in a wrapper environment that provides:
- sync_playwright: Available globally
- log_step(step_name, details): Function to log each test step
- capture_screenshot(page, name): Function to capture screenshots
- evidence_dir: Path object for saving files

REQUIREMENTS:
1. Use Playwright Python API (sync_playwright is already imported)
2. Use the provided locators - prefer the "best_locator" for each element
3. Follow the test steps exactly
4. Include proper assertions for expected results
5. **Call log_step() before each major action to log what's happening**
6. **Call capture_screenshot(page, "descriptive_name") after key steps**
7. Add comments explaining key actions
8. Handle common errors gracefully (timeouts, element not found)
9. Use descriptive variable names
10. Structure code with setup, test steps, and assertions
11. **IMPORTANT: Use Python syntax only - NO JavaScript regex /pattern/ syntax**
12. **For regex patterns in assertions, use re.compile(r"pattern") or plain strings**

OUTPUT FORMAT:
Return ONLY the Python test code. Do not include markdown code blocks or explanations.
The code should be a complete, runnable test function.

Example structure:
```python
def test_{test_case.get('id', 'test').lower().replace('-', '_')}():
    \"\"\"
    Test Case: {test_case.get('title', 'Test')}
    ID: {test_case.get('id', 'N/A')}
    Priority: {test_case.get('priority', 'N/A')}
    Type: {test_case.get('type', 'N/A')}
    \"\"\"
    from playwright.sync_api import expect
    
    with sync_playwright() as p:
        log_step("Setup: Launching browser")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            log_step("Navigate to page", {{"url": "{page_url}"}})
            page.goto("{page_url}")
            capture_screenshot(page, "page_loaded")
            
            # Locate elements using provided best_locators
            # element = page.locator("locator_from_list")
            
            # Test steps here
            log_step("Step 1: Description of step")
            # ... perform action ...
            capture_screenshot(page, "after_step1")
            
            # Assertions
            log_step("Verify: Expected result")
            # ... assertions ...
            capture_screenshot(page, "final_state")
            
        finally:
            log_step("Teardown: Closing browser")
            browser.close()
"""
        return prompt
    
    def _verify_and_correct_code(
        self,
        test_code: str,
        test_case: Dict[str, Any],
        exploration_data: Dict[str, Any],
        page_url: str,
        max_corrections: int = 2
    ) -> Dict[str, Any]:
        """
        Verify generated code and attempt self-correction if needed.
        
        Args:
            test_code: Generated test code
            test_case: Original test case
            exploration_data: Exploration data
            page_url: Page URL
            max_corrections: Maximum correction attempts
            
        Returns:
            dict: Verification and correction results
        """
        verification = self.verifier.verify_test_code(test_code, page_url)
        
        if verification["overall_status"] == "success":
            return {
                "test_id": test_case.get("id"),
                "status": "success",
                "verification": verification
            }
        
        # Attempt self-correction
        corrected_code = test_code
        correction_attempts = 0
        
        for attempt in range(max_corrections):
            if verification["overall_status"] == "success":
                break
            
            # Try to correct locators
            for check in verification.get("locator_checks", []):
                if check["result"]["status"] != "success":
                    failed_locator = check["locator"]
                    
                    # Find element index for this locator
                    element_idx = self._find_element_index_for_locator(
                        failed_locator,
                        test_case.get("related_elements", []),
                        exploration_data
                    )
                    
                    if element_idx is not None:
                        element = exploration_data["interactive_elements"][element_idx]
                        corrected_locator = auto_correct_locator(
                            failed_locator,
                            element,
                            exploration_data
                        )
                        
                        if corrected_locator:
                            # Replace in code
                            corrected_code = corrected_code.replace(
                                failed_locator,
                                corrected_locator
                            )
                            correction_attempts += 1
            
            # Re-verify after correction
            if correction_attempts > 0:
                verification = self.verifier.verify_test_code(corrected_code, page_url)
        
        return {
            "test_id": test_case.get("id"),
            "status": "success" if verification["overall_status"] == "success" else "partial",
            "verification": verification,
            "corrections_applied": correction_attempts,
            "corrected_code": corrected_code if correction_attempts > 0 else None
        }
    
    def _find_element_index_for_locator(
        self,
        locator_code: str,
        element_indices: List[int],
        exploration_data: Dict[str, Any]
    ) -> Optional[int]:
        """Find which element index corresponds to a locator code"""
        # This is a simplified matching - in practice, you'd need more sophisticated matching
        for idx in element_indices:
            if idx < len(exploration_data["interactive_elements"]):
                element = exploration_data["interactive_elements"][idx]
                # Check if locator matches element attributes
                if element.get("id") and f'#{element["id"]}' in locator_code:
                    return idx
                if element.get("name") and element["name"] in locator_code:
                    return idx
        return None
    
    def _clean_code_blocks(self, code: str) -> str:
        """Remove markdown code blocks if present"""
        # Remove ```python or ``` markers
        code = re.sub(r'```python\s*\n?', '', code)
        code = re.sub(r'```\s*\n?', '', code)
        return code.strip()
    
    def _combine_test_code(self, test_codes: List[str]) -> str:
        """Combine multiple test code snippets into a single file"""
        header = """'''
Generated Test Code - Playwright + Python
Generated by Web-Based Testing Agent
'''

from playwright.sync_api import sync_playwright
import pytest

"""
        
        combined = header + "\n\n".join(test_codes)
        return combined
    
    def cleanup(self):
        """Clean up resources"""
        if self.verifier:
            self.verifier = None

