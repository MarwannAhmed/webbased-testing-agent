"""
Phase 4: Verification & Trust Building Agent

Executes generated tests, collects evidence, and allows user review and refactoring.
"""

from typing import Dict, Any, List, Optional
import time
from utils.test_executor import TestExecutor
from utils.gemini_client import GeminiClient
from utils.browser_controller import BrowserController
import json


class VerificationAgent:
    """
    Phase 4: Verification Agent
    
    Executes tests, collects evidence (screenshots, logs), and enables
    user review and iterative improvement.
    """
    
    def __init__(self, browser: Optional[BrowserController] = None):
        self.executor = TestExecutor("results/test_execution")
        self.llm = GeminiClient()
        self.browser = browser
        self.execution_results = []
        self.evidence_collected = []
    
    def execute_tests(
        self,
        generated_code: Dict[str, Any],
        test_case_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute generated test code and collect evidence.
        
        Args:
            generated_code: Generated test code from Phase 3
            test_case_ids: Optional list of specific test IDs to execute
            
        Returns:
            dict: Execution results with evidence
        """
        print("🔍 Starting test execution and evidence collection...")
        
        test_code = generated_code.get("test_code", "")
        individual_tests = generated_code.get("individual_tests", [])
        
        if not test_code:
            return {
                "status": "error",
                "error": "No test code provided"
            }
        
        # Execute all tests or specific ones
        if test_case_ids and individual_tests:
            # Execute specific tests - handle both dict and string formats
            tests_to_run = []
            for idx, t in enumerate(individual_tests):
                if isinstance(t, dict):
                    if t.get("test_id") in test_case_ids:
                        tests_to_run.append(t)
                elif isinstance(t, str):
                    # If test is a string, create a dict for it
                    test_id = f"test_{idx}"
                    if test_id in test_case_ids or any(tid in test_id for tid in test_case_ids):
                        tests_to_run.append({"test_code": t, "test_id": test_id})
        else:
            # Execute all tests - normalize format
            if individual_tests:
                tests_to_run = []
                for idx, t in enumerate(individual_tests):
                    if isinstance(t, dict):
                        tests_to_run.append(t)
                    elif isinstance(t, str):
                        tests_to_run.append({"test_code": t, "test_id": f"test_{idx}"})
            else:
                tests_to_run = [{"test_code": test_code, "test_id": "all_tests"}]
        
        execution_results = []
        total_time = 0
        
        for test in tests_to_run:
            # Handle both dict and string formats
            if isinstance(test, dict):
                test_id = test.get("test_id", "unknown")
                test_code_snippet = test.get("test_code", test_code)
            elif isinstance(test, str):
                test_id = "unknown"
                test_code_snippet = test
            else:
                test_id = "unknown"
                test_code_snippet = test_code
            
            print(f"  Executing: {test_id}")
            
            # Execute test
            result = self.executor.execute_test_code(
                test_code=test_code_snippet,
                test_id=test_id,
                capture_screenshots=True,
                record_video=False
            )
            
            execution_results.append(result)
            total_time += result.get("execution_time", 0)
        
        # Collect all evidence
        all_screenshots = []
        all_logs = []
        
        for result in execution_results:
            all_screenshots.extend(result.get("screenshots", []))
            all_logs.extend(result.get("execution_log", []))
        
        # Generate execution report
        report = self._generate_execution_report(execution_results, all_screenshots, all_logs)
        
        self.execution_results = execution_results
        self.evidence_collected = {
            "screenshots": all_screenshots,
            "logs": all_logs,
            "report": report
        }
        
        return {
            "status": "success",
            "execution_results": execution_results,
            "evidence": self.evidence_collected,
            "summary": {
                "tests_executed": len(execution_results),
                "tests_passed": sum(1 for r in execution_results if r.get("status") == "success"),
                "tests_failed": sum(1 for r in execution_results if r.get("status") == "failed"),
                "total_execution_time": total_time,
                "screenshots_count": len(all_screenshots),
                "log_entries": len(all_logs)
            }
        }
    
    def _generate_execution_report(
        self,
        execution_results: List[Dict[str, Any]],
        screenshots: List[Dict[str, Any]],
        logs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive execution report.
        """
        report = {
            "timestamp": time.time(),
            "summary": {
                "total_tests": len(execution_results),
                "passed": sum(1 for r in execution_results if r.get("status") == "success"),
                "failed": sum(1 for r in execution_results if r.get("status") == "failed"),
                "errors": sum(1 for r in execution_results if r.get("status") == "error")
            },
            "test_details": [],
            "screenshots": screenshots,
            "execution_log": logs
        }
        
        for result in execution_results:
            test_detail = {
                "test_id": result.get("test_id"),
                "status": result.get("status"),
                "execution_time": result.get("execution_time", 0),
                "screenshots": result.get("screenshots", []),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "log_entries": len(result.get("execution_log", []))
            }
            report["test_details"].append(test_detail)
        
        return report
    
    def analyze_execution_results(
        self,
        execution_results: Dict[str, Any],
        user_critique: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze execution results and provide insights.
        
        Args:
            execution_results: Results from test execution
            user_critique: Optional user feedback/critique
            
        Returns:
            dict: Analysis and recommendations
        """
        summary = execution_results.get("summary", {})
        evidence = execution_results.get("evidence", {})
        
        # Build analysis prompt
        prompt = f"""
Analyze the test execution results and provide insights.

**Execution Summary:**
- Tests Executed: {summary.get('tests_executed', 0)}
- Tests Passed: {summary.get('tests_passed', 0)}
- Tests Failed: {summary.get('tests_failed', 0)}
- Total Execution Time: {summary.get('total_execution_time', 0):.2f}s
- Screenshots Captured: {summary.get('screenshots_count', 0)}
- Log Entries: {summary.get('log_entries', 0)}

**Test Details:**
{json.dumps(execution_results.get('execution_results', []), indent=2)}

{f"**User Critique:**\n{user_critique}" if user_critique else ""}

**Your Task:**
Provide a structured analysis in JSON format:

{{
    "overall_assessment": "Overall quality and reliability assessment",
    "strengths": ["List of strengths"],
    "issues_found": [
        {{
            "issue": "Description of issue",
            "severity": "High | Medium | Low",
            "recommendation": "How to fix"
        }}
    ],
    "recommendations": ["Actionable recommendations"],
    "trust_score": 0-100,
    "needs_refactoring": true/false,
    "refactoring_suggestions": ["Specific suggestions for improvement"]
}}

Be concise and actionable.
"""
        
        try:
            response = self.llm.generate_structured(
                prompt=prompt,
                system_instruction="You are an expert QA engineer analyzing test execution results and providing actionable feedback."
            )
            
            if response.get("status") == "success":
                from utils.json_parser import parse_llm_json_response
                analysis = parse_llm_json_response(response["text"])
                return {
                    "status": "success",
                    "analysis": analysis,
                    "tokens": response.get("total_tokens", 0)
                }
            else:
                return {
                    "status": "error",
                    "error": response.get("error", "Analysis failed")
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def refactor_test_code(
        self,
        original_code: str,
        critique: str,
        execution_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refactor test code based on user critique and execution results.
        
        Args:
            original_code: Original test code
            critique: User feedback/critique
            execution_results: Optional execution results for context
            
        Returns:
            dict: Refactored code and explanation
        """
        print("🔧 Refactoring test code based on critique...")
        
        execution_context = ""
        if execution_results:
            summary = execution_results.get("summary", {})
            execution_context = f"""
**Execution Context:**
- Tests Passed: {summary.get('tests_passed', 0)}/{summary.get('tests_executed', 0)}
- Execution Time: {summary.get('total_execution_time', 0):.2f}s
- Issues Found: {len(execution_results.get('execution_results', []))}
"""
        
        prompt = f"""
You are refactoring Playwright test code based on user critique.

**Original Test Code:**
```python
{original_code}
```

{execution_context}

**User Critique:**
{critique}

**Your Task:**
Refactor the test code to address the critique while maintaining:
- Test functionality
- Code quality
- Best practices
- Readability

Return JSON with:
{{
    "refactored_code": "The improved test code",
    "changes_made": ["List of changes"],
    "explanation": "Why these changes improve the test",
    "improvements": ["List of improvements"]
}}

Return ONLY valid JSON.
"""
        
        try:
            response = self.llm.generate_structured(
                prompt=prompt,
                system_instruction="You are an expert test automation engineer refactoring code based on feedback."
            )
            
            if response.get("status") == "success":
                from utils.json_parser import parse_llm_json_response
                refactored = parse_llm_json_response(response["text"])
                
                return {
                    "status": "success",
                    "refactored_code": refactored.get("refactored_code", original_code),
                    "changes_made": refactored.get("changes_made", []),
                    "explanation": refactored.get("explanation", ""),
                    "improvements": refactored.get("improvements", []),
                    "tokens": response.get("total_tokens", 0)
                }
            else:
                return {
                    "status": "error",
                    "error": response.get("error", "Refactoring failed")
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.cleanup()


