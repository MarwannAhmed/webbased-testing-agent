from typing import Dict, Any, List, Optional
from utils.browser_controller import BrowserController
from utils.gemini_client import GeminiClient
import json
import base64

class ExplorationAgent:
    """
    Phase 1: Exploration & Knowledge Acquisition
    
    This agent explores a web page to understand its structure, logic, and interactivity.
    It combines DOM analysis with visual understanding (screenshots) to create a 
    comprehensive representation of the page.
    """
    
    def __init__(self):
        self.browser = BrowserController()
        self.llm = GeminiClient()
        self.exploration_data = None
        
    def explore_url(self, url: str) -> Dict[str, Any]:
        """
        Main exploration method that orchestrates the entire exploration process.
        
        Args:
            url: The URL to explore
            
        Returns:
            dict: Structured representation containing:
                - page_info: Basic page metadata (title, URL, load time)
                - interactive_elements: List of all interactive elements with locators
                - page_structure: AI-generated understanding of page purpose and functionality
                - screenshot_path: Path to captured screenshot
                - metrics: Performance metrics (tokens, response time)
        """
        print(f"🔍 Starting exploration of: {url}")
        
        # Step 1: Launch browser and navigate
        navigation_result = self._navigate_to_page(url)
        if navigation_result["status"] == "error":
            return {
                "status": "error",
                "error": navigation_result["error"],
                "phase": "navigation"
            }
        
        # Step 2: Extract DOM elements
        print("📊 Extracting interactive elements from DOM...")
        elements = self._extract_elements()
        
        # Step 3: Capture screenshot for visual context
        print("📸 Capturing page screenshot...")
        screenshot_data = self._capture_screenshot()
        
        # Step 4: Analyze page with LLM
        print("🤖 Analyzing page structure with AI...")
        ai_analysis = self._analyze_page_with_llm(
            page_info=navigation_result,
            elements=elements,
            screenshot=screenshot_data
        )
        
        # Step 5: Generate structured representation
        print("✅ Building structured representation...")
        self.exploration_data = {
            "status": "success",
            "url": url,
            "page_info": navigation_result,
            "interactive_elements": elements,
            "ai_analysis": ai_analysis["analysis"],
            "screenshot_base64": screenshot_data,
            "metrics": {
                "navigation_time": navigation_result["load_time"],
                "elements_found": len(elements),
                "llm_tokens": ai_analysis["tokens"],
                "llm_response_time": ai_analysis["response_time"],
                "total_time": navigation_result["load_time"] + ai_analysis["response_time"]
            }
        }
        
        return self.exploration_data
    
    def _navigate_to_page(self, url: str) -> Dict[str, Any]:
        """
        Navigate to the target URL using the browser controller.
        Handles errors gracefully.
        """
        try:
            self.browser.launch()
            result = self.browser.navigate(url)
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_elements(self) -> List[Dict[str, Any]]:
        """
        Extract all interactive elements from the page DOM.
        Uses the browser controller's built-in element extraction.
        """
        try:
            elements = self.browser.get_interactive_elements()
            
            # Enrich elements with suggested locator strategies
            enriched_elements = []
            for idx, element in enumerate(elements):
                enriched = element.copy()
                enriched["suggested_locators"] = self._suggest_locators(element)
                enriched["element_index"] = idx
                enriched_elements.append(enriched)
            
            return enriched_elements
        except Exception as e:
            print(f"⚠️ Error extracting elements: {e}")
            return []
    
    def _suggest_locators(self, element: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Suggest multiple locator strategies for an element.
        Priority: ID > Name > CSS > XPath > Text
        """
        locators = []
        
        # ID locator (highest priority)
        if element.get("id"):
            locators.append({
                "strategy": "id",
                "value": element["id"],
                "priority": 1
            })
        
        # Name locator
        if element.get("name"):
            locators.append({
                "strategy": "name",
                "value": element["name"],
                "priority": 2
            })
        
        # CSS class locator
        if element.get("class"):
            class_name = element["class"].split()[0] if element["class"] else None
            if class_name:
                locators.append({
                    "strategy": "css",
                    "value": f".{class_name}",
                    "priority": 3
                })
        
        # Aria-label locator (for accessibility)
        if element.get("ariaLabel"):
            locators.append({
                "strategy": "aria-label",
                "value": element["ariaLabel"],
                "priority": 2
            })
        
        # Text-based locator
        if element.get("text"):
            text_snippet = element["text"][:50]
            locators.append({
                "strategy": "text",
                "value": text_snippet,
                "priority": 4
            })
        
        # XPath fallback
        xpath = self._generate_xpath(element)
        if xpath:
            locators.append({
                "strategy": "xpath",
                "value": xpath,
                "priority": 5
            })
        
        return sorted(locators, key=lambda x: x["priority"])
    
    def _generate_xpath(self, element: Dict[str, Any]) -> Optional[str]:
        """
        Generate a simple XPath for the element based on available attributes.
        """
        tag = element.get("tag", "")
        
        if element.get("id"):
            return f"//{tag}[@id='{element['id']}']"
        elif element.get("name"):
            return f"//{tag}[@name='{element['name']}']"
        elif element.get("class"):
            return f"//{tag}[@class='{element['class']}']"
        
        return None
    
    def _capture_screenshot(self) -> str:
        """
        Capture a screenshot of the current page and return as base64.
        """
        try:
            screenshot_bytes = self.browser.take_screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            return screenshot_b64
        except Exception as e:
            print(f"⚠️ Error capturing screenshot: {e}")
            return ""
    
    def _analyze_page_with_llm(self, page_info: Dict, elements: List[Dict], 
                                screenshot: str) -> Dict[str, Any]:
        """
        Use the LLM to analyze the page and provide high-level understanding.
        This creates a semantic understanding beyond just DOM structure.
        """
        # Prepare a summary of elements for the LLM (to avoid token overflow)
        element_summary = self._create_element_summary(elements)
        
        prompt = f"""You are analyzing a web page for test automation purposes.

**Page Information:**
- URL: {page_info.get('url', 'N/A')}
- Title: {page_info.get('title', 'N/A')}
- Load Time: {page_info.get('load_time', 0):.2f}s

**Interactive Elements Found:** {len(elements)}

**Element Summary:**
{element_summary}

**Your Task:**
Analyze this page and provide a structured understanding in JSON format:

{{
  "page_purpose": "Brief description of what this page does",
  "main_functionality": ["List", "of", "key", "features"],
  "user_workflows": ["Typical", "user", "journeys"],
  "testable_areas": [
    {{
      "area": "Name of testable area",
      "description": "What should be tested",
      "related_elements": ["element indices from the summary"]
    }}
  ],
  "recommended_test_priority": ["High priority areas to test first"]
}}

Be concise and focus on test automation relevance."""

        try:
            response = self.llm.generate_structured(
                prompt=prompt,
                system_instruction="You are an expert QA engineer analyzing web pages for test automation."
            )
            
            if response["status"] == "success":
                # Try to parse JSON from response
                try:
                    analysis = json.loads(response["text"])
                except json.JSONDecodeError:
                    # If JSON parsing fails, return raw text
                    analysis = {
                        "raw_analysis": response["text"],
                        "parse_error": "Could not parse JSON response"
                    }
                
                return {
                    "analysis": analysis,
                    "tokens": response["total_tokens"],
                    "response_time": response["response_time"]
                }
            else:
                return {
                    "analysis": {"error": response.get("error", "Unknown error")},
                    "tokens": 0,
                    "response_time": response["response_time"]
                }
                
        except Exception as e:
            print(f"⚠️ Error in LLM analysis: {e}")
            return {
                "analysis": {"error": str(e)},
                "tokens": 0,
                "response_time": 0
            }
    
    def _create_element_summary(self, elements: List[Dict]) -> str:
        """
        Create a concise summary of elements for LLM consumption.
        Avoids overwhelming the LLM with too much detail.
        """
        summary_lines = []
        
        for idx, elem in enumerate(elements[:50]):  # Limit to first 50 elements
            tag = elem.get("tag", "unknown")
            elem_type = elem.get("type", "")
            text = elem.get("text", "")[:30]  # Truncate text
            elem_id = elem.get("id", "")
            
            # Build a concise description
            desc_parts = [f"[{idx}]", tag]
            if elem_type:
                desc_parts.append(f"type={elem_type}")
            if elem_id:
                desc_parts.append(f"id={elem_id}")
            if text:
                desc_parts.append(f'"{text}"')
            
            summary_lines.append(" ".join(desc_parts))
        
        if len(elements) > 50:
            summary_lines.append(f"... and {len(elements) - 50} more elements")
        
        return "\n".join(summary_lines)
    
    def get_exploration_summary(self) -> str:
        """
        Generate a human-readable summary of the exploration results.
        """
        if not self.exploration_data:
            return "No exploration data available. Run explore_url() first."
        
        data = self.exploration_data
        summary = f"""
## 🔍 Exploration Summary

**URL:** {data['url']}
**Page Title:** {data['page_info'].get('title', 'N/A')}
**Status:** {data['page_info'].get('http_status', 'N/A')}

### 📊 Metrics
- **Navigation Time:** {data['metrics']['navigation_time']:.2f}s
- **Interactive Elements Found:** {data['metrics']['elements_found']}
- **AI Analysis Tokens:** {data['metrics']['llm_tokens']}
- **AI Response Time:** {data['metrics']['llm_response_time']:.2f}s
- **Total Exploration Time:** {data['metrics']['total_time']:.2f}s

### 🤖 AI Analysis
{json.dumps(data['ai_analysis'], indent=2)}
        """
        
        return summary.strip()
    
    def cleanup(self):
        """Clean up resources (close browser)"""
        self.browser.close()