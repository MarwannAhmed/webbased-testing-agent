from typing import Dict, Any, List


def build_element_lookup(exploration_data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """
    Build an index -> element dictionary to ground code generation on real elements.
    """
    lookup = {}
    for el in exploration_data.get("interactive_elements", []):
        idx = el.get("element_index")
        if idx is not None:
            lookup[int(idx)] = el
    return lookup


def choose_best_locator(element: Dict[str, Any]) -> Dict[str, str]:
    """
    Select best locator from ExplorationAgent's suggested_locators.
    Priority already sorted in exploration_agent._suggest_locators().
    """
    locs = element.get("suggested_locators", [])
    if not locs:
        return {"strategy": "css", "value": element.get("tag", "div")}

    best = locs[0]
    return {"strategy": best.get("strategy", "css"), "value": best.get("value", "")}


def playwright_locator_python(locator: Dict[str, str]) -> str:
    """
    Convert a locator strategy/value into a Playwright Python locator expression.
    Returns something like: page.get_by_label("Email") or page.locator("#id")
    """
    strategy = locator.get("strategy")
    value = locator.get("value", "")

    # Defensive
    value_escaped = value.replace('"', '\\"')

    if strategy == "id":
        return f'page.locator("#{value_escaped}")'
    if strategy == "name":
        return f'page.locator(\'[name="{value_escaped}"]\')'
    if strategy == "css":
        return f'page.locator("{value_escaped}")'
    if strategy == "xpath":
        return f'page.locator("xpath={value_escaped}")'
    if strategy == "aria-label":
        return f'page.get_by_label("{value_escaped}")'
    if strategy == "text":
        # best-effort; if text is too generic, Playwright may match multiple
        return f'page.get_by_text("{value_escaped}", exact=False)'

    return f'page.locator("{value_escaped}")'


def build_grounded_locators_block(
    test_case: Dict[str, Any],
    element_lookup: Dict[int, Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Returns a list of locator entries grounded on element indices.
    Each entry: { "element_index": "...", "strategy": "...", "value": "...", "python": "..." }
    """
    locators = []
    for idx in test_case.get("related_elements", []):
        try:
            idx_int = int(idx)
        except Exception:
            continue

        el = element_lookup.get(idx_int)
        if not el:
            continue

        best = choose_best_locator(el)
        locators.append({
            "element_index": str(idx_int),
            "tag": el.get("tag", ""),
            "text": (el.get("text") or "")[:60],
            "strategy": best["strategy"],
            "value": best["value"],
            "python": playwright_locator_python(best)
        })
    return locators


def safe_test_filename(page_url: str) -> str:
    """
    Convert URL to a safe-ish filename base. Not perfect, but good enough for local runs.
    """
    base = page_url.replace("https://", "").replace("http://", "")
    base = base.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
    return f"test_{base[:50].lower()}.py"
