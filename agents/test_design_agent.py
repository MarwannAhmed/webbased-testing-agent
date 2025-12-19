from typing import Dict, Any, List
import json
import uuid
import time
from utils.gemini_client import GeminiClient


class TestDesignAgent:
    """
    Phase 2: Collaborative Test Design

    Converts exploration data into a structured, reviewable test plan.
    The output of this agent is the SINGLE source of truth for Phase 3.
    """

    def __init__(self):
        self.llm = GeminiClient()
        self.last_test_plan = None
        self.version = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_test_plan(self, exploration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an initial test plan based on exploration results.

        Args:
            exploration_data: Output from ExplorationAgent

        Returns:
            Structured test plan (JSON-compatible dict)
        """

        prompt = self._build_generation_prompt(exploration_data)

        response = self.llm.generate_structured(
            prompt=prompt,
            system_instruction=(
                "You are a senior QA engineer designing high-quality, "
                "maintainable test plans for web automation."
            )
        )

        if response.get("status") != "success":
            raise RuntimeError(f"LLM error during test design: {response.get('error')}")

        try:
            test_plan = json.loads(response["text"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON returned by LLM: {e}")

        self.version += 1
        test_plan["metadata"] = self._build_metadata(exploration_data, response)

        self.last_test_plan = test_plan
        return test_plan

    def refine_test_plan(
        self,
        existing_plan: Dict[str, Any],
        reviewer_feedback: str
    ) -> Dict[str, Any]:
        """
        Refine an existing test plan based on human feedback.

        Args:
            existing_plan: Previously generated test plan
            reviewer_feedback: Human comments / critique

        Returns:
            Updated test plan
        """

        prompt = self._build_refinement_prompt(existing_plan, reviewer_feedback)

        response = self.llm.generate_structured(
            prompt=prompt,
            system_instruction=(
                "You are a QA engineer refining a test plan based on reviewer feedback. "
                "Preserve correctness and avoid unnecessary changes."
            )
        )

        if response.get("status") != "success":
            raise RuntimeError(f"LLM error during refinement: {response.get('error')}")

        try:
            refined_plan = json.loads(response["text"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON returned by LLM: {e}")

        self.version += 1
        refined_plan["metadata"] = self._build_metadata(
            {"url": existing_plan.get("page_url")},
            response,
            refined=True,
            feedback=reviewer_feedback
        )

        self.last_test_plan = refined_plan
        return refined_plan

    # ------------------------------------------------------------------
    # Prompt Engineering
    # ------------------------------------------------------------------

    def _build_generation_prompt(self, exploration_data: Dict[str, Any]) -> str:
        ai_analysis = exploration_data.get("ai_analysis", {})
        testable_areas = ai_analysis.get("testable_areas", [])
        elements = exploration_data.get("interactive_elements", [])

        element_index_map = [
            {
                "index": e.get("element_index"),
                "tag": e.get("tag"),
                "text": (e.get("text") or "")[:40],
                "id": e.get("id"),
            }
            for e in elements
        ]

        return f"""
You are given the results of a web page exploration.

PAGE URL:
{exploration_data.get("url")}

TESTABLE AREAS:
{json.dumps(testable_areas, indent=2)}

INTERACTIVE ELEMENT INDEX MAP:
{json.dumps(element_index_map[:30], indent=2)}

TASK:
Create a comprehensive but minimal test plan.

RULES:
- Only test functionality that clearly exists.
- Every test MUST reference real element indices.
- Include positive, negative, and edge cases where applicable.
- Prefer fewer, high-value tests.
- Assign priorities: High / Medium / Low.
- Tests must be suitable for Playwright automation.

RETURN VALID JSON ONLY IN THIS FORMAT:

{{
  "test_plan_id": "<uuid>",
  "page_url": "<url>",
  "coverage_summary": {{
    "areas_covered": <int>,
    "elements_covered": <int>,
    "risk_areas": ["..."]
  }},
  "test_cases": [
    {{
      "id": "TC_XXX_001",
      "title": "Short descriptive title",
      "priority": "High | Medium | Low",
      "type": "Functional | Validation | Navigation",
      "preconditions": ["..."],
      "steps": ["Step 1", "Step 2"],
      "expected_result": "Clear expected outcome",
      "related_elements": [1, 5, 7],
      "status": "pending_review"
    }}
  ]
}}
"""

    def _build_refinement_prompt(
        self,
        existing_plan: Dict[str, Any],
        reviewer_feedback: str
    ) -> str:
        return f"""
You are refining an existing test plan.

CURRENT TEST PLAN:
{json.dumps(existing_plan, indent=2)}

REVIEWER FEEDBACK:
"{reviewer_feedback}"

TASK:
- Apply the feedback carefully.
- Do NOT remove valid tests unless explicitly requested.
- Add or modify tests if needed.
- Preserve IDs when possible.

RETURN VALID JSON ONLY.
"""

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _build_metadata(
        self,
        exploration_data: Dict[str, Any],
        llm_response: Dict[str, Any],
        refined: bool = False,
        feedback: str = ""
    ) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": time.time(),
            "refined": refined,
            "reviewer_feedback": feedback if refined else None,
            "llm_metrics": {
                "tokens": llm_response.get("total_tokens", 0),
                "response_time": llm_response.get("response_time", 0)
            }
        }
