"""
JSON Parser Utility

Handles extraction and parsing of JSON from LLM responses.
Deals with markdown code blocks, extra text, and formatting issues.
"""

import json
import re
from typing import Dict, Any, Optional


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from text that may contain markdown, explanations, or other formatting.
    
    Args:
        text: Text that may contain JSON
        
    Returns:
        dict: Parsed JSON object, or None if extraction fails
    """
    if not text:
        return None
    
    # Try direct parsing first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    # Pattern: ```json ... ``` or ``` ... ```
    json_block_pattern = r'```(?:json)?\s*\n?(.*?)```'
    matches = re.findall(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        try:
            cleaned = match.strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON object in text (look for { ... })
    json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_object_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            # Try to balance braces
            balanced = _balance_json_braces(match)
            return json.loads(balanced)
        except json.JSONDecodeError:
            continue
    
    # Try to extract JSON array if object extraction failed
    json_array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
    matches = re.findall(json_array_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            balanced = _balance_json_brackets(match)
            return json.loads(balanced)
        except json.JSONDecodeError:
            continue
    
    return None


def _balance_json_braces(text: str) -> str:
    """
    Attempt to balance JSON braces by finding the complete JSON object.
    """
    open_count = text.count('{')
    close_count = text.count('}')
    
    if open_count == close_count:
        return text
    
    # Find the first { and try to find matching }
    start_idx = text.find('{')
    if start_idx == -1:
        return text
    
    # Count braces to find the matching closing brace
    count = 0
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            count += 1
        elif text[i] == '}':
            count -= 1
            if count == 0:
                return text[start_idx:i+1]
    
    return text


def _balance_json_brackets(text: str) -> str:
    """
    Attempt to balance JSON brackets by finding the complete JSON array.
    """
    open_count = text.count('[')
    close_count = text.count(']')
    
    if open_count == close_count:
        return text
    
    # Find the first [ and try to find matching ]
    start_idx = text.find('[')
    if start_idx == -1:
        return text
    
    # Count brackets to find the matching closing bracket
    count = 0
    for i in range(start_idx, len(text)):
        if text[i] == '[':
            count += 1
        elif text[i] == ']':
            count -= 1
            if count == 0:
                return text[start_idx:i+1]
    
    return text


def parse_llm_json_response(response_text: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse JSON from LLM response with fallback handling.
    
    Args:
        response_text: Raw response text from LLM
        fallback: Fallback dict to return if parsing fails
        
    Returns:
        dict: Parsed JSON or fallback
        
    Raises:
        ValueError: If parsing fails and no fallback provided
    """
    if not response_text or not response_text.strip():
        if fallback is not None:
            return fallback
        raise ValueError(
            "LLM returned empty response. This might indicate:\n"
            "- API quota exceeded\n"
            "- Network error\n"
            "- Model error\n"
            "Please check your API key and quota status."
        )
    
    parsed = extract_json_from_text(response_text)
    
    if parsed:
        return parsed
    
    if fallback is not None:
        return fallback
    
    # Provide helpful error message
    preview = response_text[:500] if len(response_text) > 500 else response_text
    error_msg = (
        f"Could not extract valid JSON from LLM response.\n"
        f"Response length: {len(response_text)} characters\n"
        f"Response preview:\n{preview}"
    )
    
    # Check for common issues
    if "quota" in response_text.lower() or "429" in response_text:
        error_msg += "\n\n⚠️ This might be a quota/rate limit error. Check your API quota."
    elif len(response_text.strip()) < 10:
        error_msg += "\n\n⚠️ Response is too short. The LLM might not have generated content."
    
    raise ValueError(error_msg)

