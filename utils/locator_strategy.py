"""
Locator Strategy Selection Utility

Intelligently selects the best locator strategy for elements based on:
- Element attributes (ID, name, class, etc.)
- Stability and maintainability
- Performance considerations
- Fallback mechanisms
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class LocatorStrategy(Enum):
    """Locator strategy types ordered by preference"""
    ID = "id"
    NAME = "name"
    CSS = "css"
    XPATH = "xpath"
    SEMANTIC = "semantic"  # Using text, aria-label, role, etc.
    TEXT = "text"


class LocatorSelector:
    """
    Intelligent locator strategy selector.
    
    Priority order:
    1. ID - Most stable, unique identifier
    2. NAME - Stable for form elements
    3. CSS - Good balance of readability and stability
    4. SEMANTIC - Accessibility-friendly (aria-label, role)
    5. XPATH - Flexible but brittle
    6. TEXT - Last resort, can be fragile
    """
    
    @staticmethod
    def select_best_locator(element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select the best locator strategy for an element.
        
        Args:
            element: Element dictionary from exploration data
            
        Returns:
            dict: Best locator with strategy, value, and confidence
        """
        # Check if element already has suggested locators from exploration
        if "suggested_locators" in element and element["suggested_locators"]:
            # Use the highest priority locator from exploration
            best = element["suggested_locators"][0]
            return {
                "strategy": best.get("strategy", "css"),
                "value": best.get("value", ""),
                "confidence": "high" if best.get("priority", 5) <= 2 else "medium",
                "fallbacks": element["suggested_locators"][1:3] if len(element["suggested_locators"]) > 1 else []
            }
        
        # Fallback: Generate locators from element data
        locators = LocatorSelector._generate_locators(element)
        
        if not locators:
            return {
                "strategy": "xpath",
                "value": f"//{element.get('tag', 'div')}",
                "confidence": "low",
                "fallbacks": []
            }
        
        best = locators[0]
        return {
            "strategy": best["strategy"],
            "value": best["value"],
            "confidence": "high" if best["priority"] <= 2 else "medium",
            "fallbacks": [loc for loc in locators[1:3]]
        }
    
    @staticmethod
    def _generate_locators(element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate all possible locators for an element, ordered by priority"""
        locators = []
        
        # 1. ID locator (highest priority)
        if element.get("id"):
            locators.append({
                "strategy": "id",
                "value": element["id"],
                "priority": 1,
                "playwright_code": f'page.locator("#{element["id"]}")'
            })
        
        # 2. NAME locator (for form elements)
        if element.get("name"):
            locators.append({
                "strategy": "name",
                "value": element["name"],
                "priority": 2,
                "playwright_code": f'page.locator("[name=\\"{element["name"]}\\"]")'
            })
        
        # 3. CSS class locator (use first class if multiple)
        if element.get("class"):
            classes = element["class"].split()
            if classes:
                first_class = classes[0]
                locators.append({
                    "strategy": "css",
                    "value": f".{first_class}",
                    "priority": 3,
                    "playwright_code": f'page.locator(".{first_class}")'
                })
        
        # 4. Semantic locators (aria-label, role)
        if element.get("ariaLabel"):
            locators.append({
                "strategy": "semantic",
                "value": element["ariaLabel"],
                "priority": 2,
                "playwright_code": f'page.get_by_label("{element["ariaLabel"]}")'
            })
        elif element.get("role"):
            locators.append({
                "strategy": "semantic",
                "value": element["role"],
                "priority": 3,
                "playwright_code": f'page.get_by_role("{element["role"]}")'
            })
        
        # 5. XPath locator
        xpath = LocatorSelector._generate_xpath(element)
        if xpath:
            locators.append({
                "strategy": "xpath",
                "value": xpath,
                "priority": 4,
                "playwright_code": f'page.locator("{xpath}")'
            })
        
        # 6. Text-based locator (last resort)
        if element.get("text"):
            text = element["text"].strip()[:50]  # Limit text length
            if text:
                locators.append({
                    "strategy": "text",
                    "value": text,
                    "priority": 5,
                    "playwright_code": f'page.get_by_text("{text}")'
                })
        
        # Sort by priority
        return sorted(locators, key=lambda x: x["priority"])
    
    @staticmethod
    def _generate_xpath(element: Dict[str, Any]) -> Optional[str]:
        """Generate XPath for element"""
        tag = element.get("tag", "div")
        
        if element.get("id"):
            return f"//{tag}[@id='{element['id']}']"
        elif element.get("name"):
            return f"//{tag}[@name='{element['name']}']"
        elif element.get("class"):
            # Use first class
            first_class = element["class"].split()[0] if element["class"] else None
            if first_class:
                return f"//{tag}[@class='{first_class}']"
        
        return f"//{tag}"
    
    @staticmethod
    def get_playwright_locator_code(locator: Dict[str, Any]) -> str:
        """
        Convert locator dict to Playwright code.
        
        Args:
            locator: Locator dictionary with strategy and value
            
        Returns:
            str: Playwright locator code
        """
        strategy = locator.get("strategy", "css")
        value = locator.get("value", "")
        
        if strategy == "id":
            return f'page.locator("#{value}")'
        elif strategy == "name":
            return f'page.locator("[name=\\"{value}\\"]")'
        elif strategy == "css":
            return f'page.locator("{value}")'
        elif strategy == "xpath":
            return f'page.locator("{value}")'
        elif strategy == "semantic":
            # Try to determine semantic type
            if "aria-label" in value.lower() or "label" in value.lower():
                return f'page.get_by_label("{value}")'
            elif "button" in value.lower():
                return f'page.get_by_role("button", name="{value}")'
            else:
                return f'page.get_by_text("{value}")'
        elif strategy == "text":
            return f'page.get_by_text("{value}")'
        else:
            return f'page.locator("{value}")'


def resolve_element_locator(
    element_index: int,
    exploration_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Resolve locator for an element by its index.
    
    Args:
        element_index: Index of element in exploration_data["interactive_elements"]
        exploration_data: Full exploration data from Phase 1
        
    Returns:
        dict: Best locator for the element
    """
    elements = exploration_data.get("interactive_elements", [])
    
    if element_index < 0 or element_index >= len(elements):
        return {
            "strategy": "xpath",
            "value": "//*",
            "confidence": "low",
            "error": f"Element index {element_index} out of range"
        }
    
    element = elements[element_index]
    return LocatorSelector.select_best_locator(element)


