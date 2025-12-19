"""
Test Executor

Executes generated Playwright test code and captures evidence:
- Screenshots at key steps
- Step-by-step execution logs
- Test results and metrics
- Video recording (optional)
"""

import subprocess
import tempfile
import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import base64
from io import BytesIO


class TestExecutor:
    """
    Executes Playwright test code and captures evidence.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize test executor.
        
        Args:
            output_dir: Directory to save test artifacts (screenshots, logs, etc.)
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Use temp directory
            self.output_dir = Path(tempfile.mkdtemp(prefix="test_execution_"))
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execution_log = []
        self.screenshots = []
        self.start_time = None
        self.end_time = None
    
    def execute_test_code(
        self,
        test_code: str,
        test_id: str = "test",
        capture_screenshots: bool = True,
        record_video: bool = False
    ) -> Dict[str, Any]:
        """
        Execute test code and capture evidence.
        
        Args:
            test_code: Generated Playwright test code
            test_id: Identifier for this test execution
            capture_screenshots: Whether to capture screenshots
            record_video: Whether to record video (requires additional setup)
            
        Returns:
            dict: Execution results with evidence
        """
        self.start_time = time.time()
        self.execution_log = []
        self.screenshots = []
        
        # Create test file
        test_file = self.output_dir / f"{test_id}.py"
        test_file.write_text(test_code, encoding='utf-8')
        
        # Create a wrapper script that captures evidence
        wrapper_code = self._create_wrapper_script(str(test_file), capture_screenshots)
        wrapper_file = self.output_dir / f"{test_id}_wrapper.py"
        wrapper_file.write_text(wrapper_code, encoding='utf-8')
        
        try:
            # Execute the test
            result = self._run_test(wrapper_file, test_id)
            
            self.end_time = time.time()
            execution_time = self.end_time - self.start_time
            
            return {
                "status": "success" if result["exit_code"] == 0 else "failed",
                "test_id": test_id,
                "execution_time": execution_time,
                "exit_code": result["exit_code"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "execution_log": self.execution_log,
                "screenshots": self.screenshots,
                "evidence_dir": str(self.output_dir),
                "test_file": str(test_file),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
            
        except Exception as e:
            self.end_time = time.time()
            execution_time = self.end_time - self.start_time if self.start_time else 0
            
            return {
                "status": "error",
                "test_id": test_id,
                "execution_time": execution_time,
                "error": str(e),
                "execution_log": self.execution_log,
                "screenshots": self.screenshots,
                "evidence_dir": str(self.output_dir)
            }
    
    def _create_wrapper_script(self, test_file_path: str, capture_screenshots: bool) -> str:
        """
        Create a wrapper script that executes test code with evidence capture.
        """
        # Escape the paths for use in string
        evidence_dir_str = str(self.output_dir).replace("\\", "\\\\")
        test_file_str = test_file_path.replace("\\", "\\\\")
        
        wrapper = f"""import sys
import json
import traceback
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import base64

# Evidence collection
evidence_dir = Path(r"{evidence_dir_str}")
evidence_dir.mkdir(parents=True, exist_ok=True)

execution_log = []
screenshots = []

def log_step(step_name, details=None):
    '''Log a test step'''
    log_entry = {{
        "timestamp": time.time(),
        "step": step_name,
        "details": details or {{}}
    }}
    execution_log.append(log_entry)
    print(f"[LOG] {{step_name}}", file=sys.stderr)

def capture_screenshot(page, name):
    '''Capture screenshot and save'''
    try:
        screenshot_path = evidence_dir / f"{{name}}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        # Read and encode as base64
        with open(screenshot_path, "rb") as f:
            screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        screenshots.append({{
            "name": name,
            "path": str(screenshot_path),
            "base64": screenshot_b64,
            "timestamp": time.time()
        }})
        return screenshot_b64
    except Exception as e:
        print(f"[ERROR] Screenshot capture failed: {{e}}", file=sys.stderr)
        return None

try:
    # Execute the test code from file
    test_file = Path(r"{test_file_str}")
    
    # Read test code
    with open(test_file, "r", encoding="utf-8") as f:
        test_code = f.read()
    
    # Execute in controlled environment
    exec_globals = {{
        "sync_playwright": sync_playwright,
        "log_step": log_step,
        "capture_screenshot": capture_screenshot,
        "evidence_dir": evidence_dir,
        "Path": Path,
        "time": time
    }}
    
    exec(test_code, exec_globals)
    
    # Save execution log
    log_file = evidence_dir / "execution_log.json"
    with open(log_file, "w") as f:
        json.dump(execution_log, f, indent=2)
    
    # Save screenshots metadata
    screenshots_file = evidence_dir / "screenshots.json"
    with open(screenshots_file, "w") as f:
        json.dump(screenshots, f, indent=2)
    
    print("[SUCCESS] Test execution completed", file=sys.stderr)
    sys.exit(0)
    
except AssertionError as e:
    print(f"[ASSERTION_ERROR] {{e}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] Test execution failed: {{e}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        return wrapper
    
    def _run_test(self, test_file: Path, test_id: str) -> Dict[str, Any]:
        """
        Run the test file and capture output.
        """
        try:
            # Run the test
            process = subprocess.Popen(
                ["python", str(test_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.output_dir)
            )
            
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            # Parse execution log if available
            log_file = self.output_dir / "execution_log.json"
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        self.execution_log = json.load(f)
                except:
                    pass
            
            # Parse screenshots if available
            screenshots_file = self.output_dir / "screenshots.json"
            if screenshots_file.exists():
                try:
                    with open(screenshots_file, "r") as f:
                        self.screenshots = json.load(f)
                except:
                    pass
            
            # Extract errors and warnings from stderr
            errors = []
            warnings = []
            
            for line in stderr.split('\n'):
                if '[ERROR]' in line or '[ASSERTION_ERROR]' in line:
                    errors.append(line)
                elif '[WARNING]' in line:
                    warnings.append(line)
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "errors": [str(e)],
                "warnings": []
            }
    
    def get_evidence_summary(self) -> Dict[str, Any]:
        """
        Get summary of captured evidence.
        """
        return {
            "execution_log_entries": len(self.execution_log),
            "screenshots_count": len(self.screenshots),
            "evidence_directory": str(self.output_dir),
            "execution_time": self.end_time - self.start_time if self.start_time and self.end_time else 0
        }
    
    def cleanup(self):
        """Clean up temporary files"""
        # Optionally remove temp directory
        # import shutil
        # if self.output_dir.exists() and str(self.output_dir).startswith(tempfile.gettempdir()):
        #     shutil.rmtree(self.output_dir)
        pass

