"""
Code Verifier for Self-Correction

Verifies generated test code by:
- Checking if locators can find elements
- Validating code syntax
- Testing code execution in a controlled environment
- Providing feedback for corrections
"""

from typing import Dict, Any, List, Optional, Tuple
from utils.browser_controller import BrowserController
import re
import ast
import traceback


class CodeVerifier:
    """
    Verifies and corrects generated test code.
    Implements self-correction mechanisms.
    """
    
    def __init__(self, browser: Optional[BrowserController] = None):
        self.browser = browser
        self.verification_results = []
    
    def verify_locator(self, locator_code: str, page_url: str) -> Dict[str, Any]:
        """
        Verify if a locator can find an element on the page.
        
        Args:
            locator_code: Playwright locator code (e.g., 'page.locator("#id")')
            page_url: URL of the page to test on
            
        Returns:
            dict: Verification result with success status and feedback
        """
        if not self.browser or not self.browser.page:
            return {
                "status": "error",
                "error": "Browser not available for verification",
                "suggestion": "Ensure browser is launched"
            }
        
        try:
            # Navigate to page if needed
            current_url = self.browser.page.url
            if current_url != page_url:
                self.browser.navigate(page_url)
            
            # Extract the locator selector from code
            selector = self._extract_selector_from_code(locator_code)
            
            if not selector:
                return {
                    "status": "error",
                    "error": "Could not extract selector from locator code",
                    "suggestion": "Use standard Playwright locator syntax"
                }
            
            # Try to find the element
            try:
                # Execute JavaScript to check if element exists
                # Clean selector - remove quotes if present
                clean_selector = selector.strip('"\'')
                
                check_script = f"""
                () => {{
                    try {{
                        const selector = "{clean_selector}";
                        const element = document.querySelector(selector);
                        return {{
                            found: element !== null,
                            visible: element ? (element.offsetWidth > 0 && element.offsetHeight > 0) : false,
                            tag: element ? element.tagName : null
                        }};
                    }} catch (e) {{
                        return {{ found: false, error: e.message }};
                    }}
                }}
                """
                
                result = self.browser.execute_script(check_script)
                
                if result.get("found"):
                    return {
                        "status": "success",
                        "found": True,
                        "visible": result.get("visible", False),
                        "tag": result.get("tag"),
                        "confidence": "high" if result.get("visible") else "medium"
                    }
                else:
                    return {
                        "status": "error",
                        "found": False,
                        "error": result.get("error", "Element not found"),
                        "suggestion": "Try alternative locator strategy or verify element exists"
                    }
                    
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "suggestion": "Locator syntax may be invalid"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "suggestion": "Browser navigation or execution failed"
            }
    
    def verify_code_syntax(self, code: str) -> Dict[str, Any]:
        """
        Verify Python code syntax.
        
        Args:
            code: Python code string
            
        Returns:
            dict: Syntax verification result
        """
        try:
            ast.parse(code)
            return {
                "status": "success",
                "syntax_valid": True
            }
        except SyntaxError as e:
            return {
                "status": "error",
                "syntax_valid": False,
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset,
                "suggestion": f"Fix syntax error at line {e.lineno}: {e.msg}"
            }
        except Exception as e:
            return {
                "status": "error",
                "syntax_valid": False,
                "error": str(e),
                "suggestion": "Unexpected error during syntax check"
            }
    
    def verify_test_code(self, test_code: str, page_url: str) -> Dict[str, Any]:
        """
        Comprehensive verification of generated test code.
        
        Args:
            test_code: Complete test code string
            page_url: URL to test against
            
        Returns:
            dict: Comprehensive verification results
        """
        results = {
            "syntax_check": None,
            "locator_checks": [],
            "overall_status": "pending",
            "issues": [],
            "suggestions": []
        }
        
        # 1. Check syntax
        syntax_result = self.verify_code_syntax(test_code)
        results["syntax_check"] = syntax_result
        
        if syntax_result["status"] != "success":
            results["overall_status"] = "error"
            results["issues"].append("Syntax error in generated code")
            return results
        
        # 2. Extract and verify locators
        locators = self._extract_locators_from_code(test_code)
        
        for locator in locators:
            if self.browser and self.browser.page:
                locator_result = self.verify_locator(locator, page_url)
                results["locator_checks"].append({
                    "locator": locator,
                    "result": locator_result
                })
                
                if locator_result["status"] != "success":
                    results["issues"].append(f"Locator failed: {locator}")
                    results["suggestions"].append(locator_result.get("suggestion", ""))
        
        # 3. Determine overall status
        if not results["issues"]:
            results["overall_status"] = "success"
        elif len(results["issues"]) < len(locators):
            results["overall_status"] = "partial"
        else:
            results["overall_status"] = "error"
        
        return results
    
    def _extract_selector_from_code(self, locator_code: str) -> Optional[str]:
        """
        Extract CSS selector or XPath from Playwright locator code.
        
        Args:
            locator_code: Playwright locator code string
            
        Returns:
            str: Extracted selector, or None if extraction fails
        """
        # Pattern: page.locator("#id") -> "#id"
        # Pattern: page.locator(".class") -> ".class"
        # Pattern: page.locator("//xpath") -> "//xpath"
        # Pattern: page.get_by_text("text") -> text-based (handle differently)
        
        # Extract string from locator()
        match = re.search(r'locator\(["\']([^"\']+)["\']\)', locator_code)
        if match:
            return f'"{match.group(1)}"'
        
        # Extract from get_by_text
        match = re.search(r'get_by_text\(["\']([^"\']+)["\']\)', locator_code)
        if match:
            text = match.group(1)
            # Convert to XPath for verification
            return f'"//*[contains(text(), \\"{text}\\")]"'
        
        # Extract from get_by_label
        match = re.search(r'get_by_label\(["\']([^"\']+)["\']\)', locator_code)
        if match:
            label = match.group(1)
            return f'"//label[contains(text(), \\"{label}\\")]//following-sibling::*[1] | //*[@aria-label=\\"{label}\\"]"'
        
        return None
    
    def _extract_locators_from_code(self, code: str) -> List[str]:
        """
        Extract all locator code snippets from test code.
        
        Args:
            code: Test code string
            
        Returns:
            list: List of locator code strings
        """
        locators = []
        
        # Pattern: page.locator(...)
        locator_pattern = r'page\.locator\([^)]+\)'
        locators.extend(re.findall(locator_pattern, code))
        
        # Pattern: page.get_by_*()
        get_by_pattern = r'page\.get_by_\w+\([^)]+\)'
        locators.extend(re.findall(get_by_pattern, code))
        
        return locators
    
    def suggest_corrections(self, verification_result: Dict[str, Any]) -> List[str]:
        """
        Suggest corrections based on verification results.
        
        Args:
            verification_result: Result from verify_test_code()
            
        Returns:
            list: List of correction suggestions
        """
        suggestions = []
        
        if verification_result["overall_status"] == "error":
            if verification_result["syntax_check"] and verification_result["syntax_check"]["status"] != "success":
                suggestions.append("Fix syntax errors first")
            
            for check in verification_result["locator_checks"]:
                if check["result"]["status"] != "success":
                    suggestions.append(f"Try alternative locator for: {check['locator']}")
                    if "suggestion" in check["result"]:
                        suggestions.append(check["result"]["suggestion"])
        
        return suggestions


def auto_correct_locator(
    failed_locator: str,
    element_data: Dict[str, Any],
    exploration_data: Dict[str, Any]
) -> Optional[str]:
    """
    Automatically suggest a corrected locator when one fails.
    
    Args:
        failed_locator: The locator that failed
        element_data: Element information from exploration
        exploration_data: Full exploration data
        
    Returns:
        str: Suggested corrected locator code, or None
    """
    from utils.locator_strategy import LocatorSelector
    
    # Get all possible locators for this element
    all_locators = LocatorSelector._generate_locators(element_data)
    
    # Find the failed locator and try the next one
    failed_strategy = None
    if "get_by_text" in failed_locator:
        failed_strategy = "text"
    elif "get_by_label" in failed_locator:
        failed_strategy = "semantic"
    elif 'locator("#' in failed_locator:
        failed_strategy = "id"
    elif 'locator("[name=' in failed_locator:
        failed_strategy = "name"
    elif 'locator(".' in failed_locator:
        failed_strategy = "css"
    elif 'locator("//' in failed_locator:
        failed_strategy = "xpath"
    
    # Find next best locator
    if failed_strategy:
        for locator in all_locators:
            if locator["strategy"] != failed_strategy:
                return locator.get("playwright_code", "")
    
    # Fallback: return first available locator
    if all_locators:
        return all_locators[0].get("playwright_code", "")
    
    return None

