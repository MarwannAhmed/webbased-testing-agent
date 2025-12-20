from typing import Dict, Any
import json
import time

from utils.gemini_client import GeminiClient
from utils.playwright_codegen_controller import (
    build_element_lookup,
    build_grounded_locators_block
)


class ImplementationAgent:
    """
    Phase 3: Implementation (Code Generation)

    Input:
      - exploration_data (Phase 1)
      - approved test_plan (Phase 2)

    Output:
      - runnable Playwright + Python test code (pytest style)
    """

    def __init__(self):
        self.llm = GeminiClient()
        self.version = 0
        self.last_generated = None

    def generate_playwright_tests(
        self,
        exploration_data: Dict[str, Any],
        test_plan: Dict[str, Any],
        use_pytest: bool = True
    ) -> Dict[str, Any]:
        start = time.time()
        self.version += 1

        element_lookup = build_element_lookup(exploration_data)

        # Build grounded payload for LLM: testcases + locator hints derived from actual elements
        grounded_cases = []
        for tc in test_plan.get("test_cases", []):
            grounded_cases.append({
                "id": tc.get("id"),
                "title": tc.get("title"),
                "priority": tc.get("priority"),
                "type": tc.get("type"),
                "preconditions": tc.get("preconditions", []),
                "steps": tc.get("steps", []),
                "expected_result": tc.get("expected_result", ""),
                "locators": build_grounded_locators_block(tc, element_lookup)
            })

        prompt = self._build_codegen_prompt(
            page_url=test_plan.get("page_url", exploration_data.get("url", "")),
            grounded_cases=grounded_cases,
            use_pytest=use_pytest
        )

        response = self.llm.generate(
            prompt=prompt,
            system_instruction=(
                "You are an expert QA automation engineer. "
                "Generate clean, runnable Playwright Python tests grounded on provided locators. "
                "Do not invent UI elements."
            )
        )

        if response.get("status") != "success":
            raise RuntimeError(response.get("error", "Playwright code generation failed"))

        code = response.get("text", "").strip()

        result = {
            "status": "success",
            "code": code,
            "metadata": {
                "version": self.version,
                "timestamp": time.time(),
                "generation_time": time.time() - start,
                "llm_tokens": response.get("total_tokens", 0),
                "llm_response_time": response.get("response_time", 0)
            }
        }

        self.last_generated = result
        return result

    def _build_codegen_prompt(self, page_url: str, grounded_cases: Any, use_pytest: bool) -> str:
        framework = "pytest + Playwright sync API" if use_pytest else "Playwright sync API"

        # IMPORTANT: We keep the LLM’s job simple:
        # - Use locators we provide
        # - Implement steps with reasonable assumptions (fill/click)
        # - Add basic assertions aligned to expected_result without inventing pages
        return f"""
Generate {framework} test code.

TARGET URL:
{page_url}

GROUND RULES (VERY IMPORTANT):
- You MUST only use the provided locator hints for interactions (locators[].python).
- Do NOT create new selectors or reference elements not in locator hints.
- If a step cannot be implemented with given locators, implement it as a TODO comment (do not hallucinate).
- Use readable helper functions.
- Add screenshots on failure (pytest hook or try/except).
- Each test case must map to one test function named test_<id_lowercase>.
- Keep the code runnable.

TEST CASES (GROUND TRUTH + LOCATOR HINTS):
{json.dumps(grounded_cases, indent=2)}

OUTPUT REQUIREMENTS:
- Return ONLY python code (no markdown).
- Include imports.
- Use Playwright sync API.
- Use pytest fixtures for browser/page if possible.
"""
