from typing import Dict, List, Set
import uuid


# ==============================================================
# IDS
# ==============================================================

def generate_test_plan_id() -> str:
    return f"TP_{uuid.uuid4().hex[:8].upper()}"


def normalize_test_case_ids(test_cases: List[Dict]) -> List[Dict]:
    """
    Ensure stable, readable, sequential test case IDs.
    """
    normalized = []

    for idx, tc in enumerate(test_cases, start=1):
        tc = tc.copy()
        tc["id"] = f"TC_{idx:03d}"
        normalized.append(tc)

    return normalized


# ==============================================================
# COVERAGE
# ==============================================================

def compute_element_coverage(test_cases: List[Dict]) -> Set[int]:
    covered = set()
    for tc in test_cases:
        for el in tc.get("related_elements", []):
            covered.add(el)
    return covered


def build_coverage_summary(
    test_cases: List[Dict],
    total_elements: int,
    testable_areas: List[Dict]
) -> Dict:
    covered_elements = compute_element_coverage(test_cases)

    risk_areas = [
        area["area"]
        for area in testable_areas
        if not area.get("related_elements")
    ]

    coverage_percent = (
        round((len(covered_elements) / total_elements) * 100, 2)
        if total_elements else 0
    )

    return {
        "areas_covered": len(testable_areas),
        "elements_covered": len(covered_elements),
        "elements_total": total_elements,
        "coverage_percent": coverage_percent,
        "risk_areas": risk_areas
    }
