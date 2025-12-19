from typing import Dict, Any, List
import json
import time

from utils.gemini_client import GeminiClient
from utils.test_plan_controller import (
    generate_test_plan_id,
    normalize_test_case_ids,
    build_coverage_summary
)


class TestDesignAgent:
    """
    Phase 2: Collaborative Test Design Agent

    Responsible for converting exploration output into a structured,
    reviewable, and executable test plan.
    """

    def __init__(self):
        self.llm = GeminiClient()
        self.version = 0
        self.last_test_plan = None

    # ==============================================================
    # PUBLIC API
    # ==============================================================

    def generate_test_plan(self, exploration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an initial test plan from exploration data.
        """

        prompt = self._build_generation_prompt(exploration_data)

        response = self.llm.generate_structured(
            prompt=prompt,
            system_instruction=(
                "You are a senior QA engineer designing precise, "
                "grounded, and automation-ready test plans."
            )
        )

        if response.get("status") != "success":
            raise RuntimeError(response.get("error", "Test design failed"))

        try:
            raw_plan = json.loads(response["text"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}")

        self.version += 1

        # Normalize + enrich deterministically
        raw_plan["test_plan_id"] = generate_test_plan_id()
        raw_plan["page_url"] = exploration_data["url"]
        raw_plan["test_cases"] = normalize_test_case_ids(raw_plan["test_cases"])

        raw_plan["coverage_summary"] = build_coverage_summary(
            test_cases=raw_plan["test_cases"],
            total_elements=len(exploration_data["interactive_elements"]),
            testable_areas=exploration_data["ai_analysis"].get("testable_areas", [])
        )

        raw_plan["metadata"] = self._build_metadata(response)

        self.last_test_plan = raw_plan
        return raw_plan

    def refine_test_plan(
        self,
        existing_plan: Dict[str, Any],
        reviewer_feedback: str
    ) -> Dict[str, Any]:
        """
        Refine an existing test plan based on human feedback.
        """

        prompt = self._build_refinement_prompt(existing_plan, reviewer_feedback)

        response = self.llm.generate_structured(
            prompt=prompt,
            system_instruction=(
                "You are a QA engineer refining a test plan based on human feedback. "
                "Preserve correctness and avoid unnecessary changes."
            )
        )

        if response.get("status") != "success":
            raise RuntimeError(response.get("error", "Refinement failed"))

        try:
            refined_plan = json.loads(response["text"])
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}")

        self.version += 1

        refined_plan["test_cases"] = normalize_test_case_ids(refined_plan["test_cases"])
        refined_plan["coverage_summary"] = build_coverage_summary(
            test_cases=refined_plan["test_cases"],
            total_elements=existing_plan["coverage_summary"]["elements_total"],
            testable_areas=[]
        )

        refined_plan["metadata"] = self._build_metadata(
            response,
            refined=True,
            feedback=reviewer_feedback
        )

        self.last_test_plan = refined_plan
        return refined_plan

    # ==============================================================
    # PROMPTS
    # ==============================================================

    def _build_generation_prompt(self, exploration_data: Dict[str, Any]) -> str:
        elements = exploration_data["interactive_elements"]

        element_map = [
            {
                "index": e["element_index"],
                "tag": e["tag"],
                "text": (e.get("text") or "")[:40],
                "id": e.get("id")
            }
            for e in elements[:40]
        ]

        return f"""
You are given exploration results of a web page.

URL:
{exploration_data["url"]}

TESTABLE AREAS:
{json.dumps(exploration_data["ai_analysis"].get("testable_areas", []), indent=2)}

INTERACTIVE ELEMENT MAP:
{json.dumps(element_map, indent=2)}

TASK:
Create a minimal but complete test plan.

RULES:
- Do NOT invent functionality.
- Every test must reference real element indices.
- Include positive, negative, and edge cases when relevant.
- Tests must be suitable for Playwright automation.
- Assign priority: High, Medium, Low.

RETURN VALID JSON ONLY IN THIS FORMAT:

{{
  "test_cases": [
    {{
      "title": "Descriptive test title",
      "priority": "High | Medium | Low",
      "type": "Functional | Validation | Navigation",
      "preconditions": ["..."],
      "steps": ["Step 1", "Step 2"],
      "expected_result": "Expected outcome",
      "related_elements": [1, 2],
      "status": "pending_review"
    }}
  ]
}}
"""

    def _build_refinement_prompt(
        self,
        existing_plan: Dict[str, Any],
        feedback: str
    ) -> str:
        return f"""
You are refining an existing test plan.

CURRENT TEST PLAN:
{json.dumps(existing_plan, indent=2)}

REVIEWER FEEDBACK:
"{feedback}"

TASK:
- Apply the feedback carefully.
- Keep test IDs stable when possible.
- Do not remove valid tests unless explicitly requested.

RETURN VALID JSON ONLY.
"""

    # ==============================================================
    # METADATA
    # ==============================================================

    def _build_metadata(
        self,
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
