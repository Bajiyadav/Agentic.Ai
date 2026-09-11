import os
import sys
import time
import json
import shutil
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TestCase(BaseModel):
    id: Optional[str] = None
    input_data: Any = None
    expected_output: Any = None
    description: Optional[str] = None
    hidden: bool = False

class TestCaseResult(BaseModel):
    test_index: int
    description: Optional[str] = None
    expected: Any = None
    actual: Any = None
    passed: bool
    error: Optional[str] = None

class SandboxExecutionResult(BaseModel):
    language: str
    success: bool
    all_passed: bool
    tests_passed: int
    total_tests: int
    test_results: List[TestCaseResult] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None

class SandboxService:
    """
    Multi-language server-side code execution sandbox supporting
    Python, JavaScript (Node.js), Go, and Java with safety timeouts and test runners.
    """
    TIMEOUT_SECONDS = 5.0

    @classmethod
    def execute_code(
        cls,
        language: str,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        custom_input: Optional[str] = None
    ) -> SandboxExecutionResult:
        lang = (language or "python").lower().strip()
        if lang in ("py", "python3"):
            lang = "python"
        elif lang in ("js", "nodejs"):
            lang = "javascript"

        if lang == "python":
            return cls._execute_python(code, test_cases, custom_input)
        elif lang == "javascript":
            return cls._execute_javascript(code, test_cases, custom_input)
        elif lang == "go":
            return cls._execute_go(code, test_cases, custom_input)
        elif lang == "java":
            return cls._execute_java(code, test_cases, custom_input)
        elif lang in ("sql", "sqlite", "sqlite3", "postgresql"):
            return cls._execute_sql(code, test_cases, custom_input)
        else:
            return SandboxExecutionResult(
                language=language,
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=0,
                error_message=f"Unsupported sandbox language: {language}. Supported languages: python, javascript, go, java, sql"
            )

    @classmethod
    def _execute_python(
        cls,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str]
    ) -> SandboxExecutionResult:
        temp_dir = tempfile.mkdtemp(prefix="sandbox_py_")
        script_path = os.path.join(temp_dir, "solution.py")
        start_time = time.time()

        # Build runner wrapper
        harness = code + "\n\n"
        if test_cases:
            harness += """
import json

_test_cases = json.loads(""" + json.dumps(json.dumps(test_cases)) + """)
_results = []

def _normalize(val):
    try:
        return json.dumps(val, sort_keys=True)
    except Exception:
        return str(val)

# Execute test cases
for idx, tc in enumerate(_test_cases):
    inp = tc.get("input_data")
    expected = tc.get("expected_output")
    desc = tc.get("description", f"Test {idx + 1}")
    try:
        if isinstance(inp, list):
            # Try unpacking arguments if multiple args
            if "solution" in globals():
                res = solution(*inp)
            elif "solve" in globals():
                res = solve(*inp)
            else:
                res = None
                raise NameError("Entry function 'solution' or 'solve' not found.")
        elif isinstance(inp, dict):
            if "solution" in globals():
                res = solution(**inp)
            elif "solve" in globals():
                res = solve(**inp)
            else:
                res = None
                raise NameError("Entry function 'solution' or 'solve' not found.")
        elif inp is not None:
            if "solution" in globals():
                res = solution(inp)
            elif "solve" in globals():
                res = solve(inp)
            else:
                res = None
                raise NameError("Entry function 'solution' or 'solve' not found.")
        else:
            if "solution" in globals():
                res = solution()
            elif "solve" in globals():
                res = solve()
            else:
                res = None

        passed = (_normalize(res) == _normalize(expected)) or (res == expected)
        _results.append({
            "test_index": idx + 1,
            "description": desc,
            "expected": expected,
            "actual": res,
            "passed": bool(passed),
            "error": None
        })
    except Exception as e:
        _results.append({
            "test_index": idx + 1,
            "description": desc,
            "expected": expected,
            "actual": None,
            "passed": False,
            "error": str(e)
        })

print("__SANDBOX_TEST_RESULTS__" + json.dumps(_results))
"""
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(harness)

            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            res = subprocess.run(
                [sys.executable, "-I", script_path],
                cwd=temp_dir,
                input=custom_input.encode("utf-8") if custom_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=cls.TIMEOUT_SECONDS,
                env=env
            )
            elapsed_ms = (time.time() - start_time) * 1000.0
            stdout_str = res.stdout.decode("utf-8", errors="replace")
            stderr_str = res.stderr.decode("utf-8", errors="replace")

            return cls._parse_results("python", stdout_str, stderr_str, elapsed_ms, res.returncode == 0)

        except subprocess.TimeoutExpired:
            return SandboxExecutionResult(
                language="python",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                execution_time_ms=cls.TIMEOUT_SECONDS * 1000.0,
                error_message=f"Execution timed out (> {cls.TIMEOUT_SECONDS}s). Check for infinite loops."
            )
        except Exception as e:
            return SandboxExecutionResult(
                language="python",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message=str(e)
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _execute_javascript(
        cls,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str]
    ) -> SandboxExecutionResult:
        temp_dir = tempfile.mkdtemp(prefix="sandbox_js_")
        script_path = os.path.join(temp_dir, "solution.js")
        start_time = time.time()

        harness = code + "\n\n"
        if test_cases:
            harness += """
const _testCases = """ + json.dumps(test_cases) + """;
const _results = [];

function _normalize(val) {
    try {
        return JSON.stringify(val);
    } catch(e) {
        return String(val);
    }
}

for (let idx = 0; idx < _testCases.length; idx++) {
    const tc = _testCases[idx];
    const inp = tc.input_data;
    const expected = tc.expected_output;
    const desc = tc.description || `Test ${idx + 1}`;
    try {
        let fn = typeof solution === 'function' ? solution : (typeof solve === 'function' ? solve : null);
        if (!fn) throw new Error("Entry function 'solution' or 'solve' not found.");
        let res;
        if (Array.isArray(inp)) {
            res = fn(...inp);
        } else if (inp !== undefined && inp !== null) {
            res = fn(inp);
        } else {
            res = fn();
        }
        const passed = _normalize(res) === _normalize(expected);
        _results.push({
            test_index: idx + 1,
            description: desc,
            expected: expected,
            actual: res,
            passed: passed,
            error: null
        });
    } catch(e) {
        _results.push({
            test_index: idx + 1,
            description: desc,
            expected: expected,
            actual: null,
            passed: false,
            error: e.message || String(e)
        });
    }
}
console.log("__SANDBOX_TEST_RESULTS__" + JSON.stringify(_results));
"""
        node_bin = shutil.which("node") or "node"
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(harness)

            res = subprocess.run(
                [node_bin, script_path],
                cwd=temp_dir,
                input=custom_input.encode("utf-8") if custom_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=cls.TIMEOUT_SECONDS
            )
            elapsed_ms = (time.time() - start_time) * 1000.0
            stdout_str = res.stdout.decode("utf-8", errors="replace")
            stderr_str = res.stderr.decode("utf-8", errors="replace")

            return cls._parse_results("javascript", stdout_str, stderr_str, elapsed_ms, res.returncode == 0)

        except FileNotFoundError:
            return SandboxExecutionResult(
                language="javascript",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message="Node.js runtime not installed on host machine."
            )
        except subprocess.TimeoutExpired:
            return SandboxExecutionResult(
                language="javascript",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                execution_time_ms=cls.TIMEOUT_SECONDS * 1000.0,
                error_message=f"Execution timed out (> {cls.TIMEOUT_SECONDS}s)."
            )
        except Exception as e:
            return SandboxExecutionResult(
                language="javascript",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message=str(e)
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _execute_go(
        cls,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str]
    ) -> SandboxExecutionResult:
        go_bin = shutil.which("go")
        if not go_bin:
            return SandboxExecutionResult(
                language="go",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message="Go toolchain (go) is not installed on host machine."
            )

        temp_dir = tempfile.mkdtemp(prefix="sandbox_go_")
        file_path = os.path.join(temp_dir, "main.go")
        start_time = time.time()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            res = subprocess.run(
                [go_bin, "run", "main.go"],
                cwd=temp_dir,
                input=custom_input.encode("utf-8") if custom_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=cls.TIMEOUT_SECONDS + 3.0  # extra build time
            )
            elapsed_ms = (time.time() - start_time) * 1000.0
            stdout_str = res.stdout.decode("utf-8", errors="replace")
            stderr_str = res.stderr.decode("utf-8", errors="replace")
            return cls._parse_results("go", stdout_str, stderr_str, elapsed_ms, res.returncode == 0)

        except subprocess.TimeoutExpired:
            return SandboxExecutionResult(
                language="go",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                execution_time_ms=cls.TIMEOUT_SECONDS * 1000.0,
                error_message="Go execution timed out."
            )
        except Exception as e:
            return SandboxExecutionResult(
                language="go",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message=str(e)
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _execute_java(
        cls,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str]
    ) -> SandboxExecutionResult:
        javac_bin = shutil.which("javac")
        java_bin = shutil.which("java")
        if not javac_bin or not java_bin:
            return SandboxExecutionResult(
                language="java",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message="Java JDK (javac/java) is not installed on host machine."
            )

        temp_dir = tempfile.mkdtemp(prefix="sandbox_java_")
        file_path = os.path.join(temp_dir, "Solution.java")
        start_time = time.time()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Compile
            comp = subprocess.run(
                [javac_bin, "Solution.java"],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=cls.TIMEOUT_SECONDS
            )
            if comp.returncode != 0:
                return SandboxExecutionResult(
                    language="java",
                    success=False,
                    all_passed=False,
                    tests_passed=0,
                    total_tests=len(test_cases or []),
                    stderr=comp.stderr.decode("utf-8", errors="replace"),
                    error_message="Java compilation error"
                )

            # Run
            res = subprocess.run(
                [java_bin, "Solution"],
                cwd=temp_dir,
                input=custom_input.encode("utf-8") if custom_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=cls.TIMEOUT_SECONDS
            )
            elapsed_ms = (time.time() - start_time) * 1000.0
            stdout_str = res.stdout.decode("utf-8", errors="replace")
            stderr_str = res.stderr.decode("utf-8", errors="replace")
            return cls._parse_results("java", stdout_str, stderr_str, elapsed_ms, res.returncode == 0)

        except subprocess.TimeoutExpired:
            return SandboxExecutionResult(
                language="java",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                execution_time_ms=cls.TIMEOUT_SECONDS * 1000.0,
                error_message="Java execution timed out."
            )
        except Exception as e:
            return SandboxExecutionResult(
                language="java",
                success=False,
                all_passed=False,
                tests_passed=0,
                total_tests=len(test_cases or []),
                error_message=str(e)
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _parse_results(
        cls,
        language: str,
        stdout_str: str,
        stderr_str: str,
        elapsed_ms: float,
        success: bool
    ) -> SandboxExecutionResult:
        import json

        delimiter = "__SANDBOX_TEST_RESULTS__"
        clean_stdout = stdout_str
        test_results = []
        tests_passed = 0
        total_tests = 0

        if delimiter in stdout_str:
            parts = stdout_str.split(delimiter, 1)
            clean_stdout = parts[0].strip()
            raw_json = parts[1].strip()
            try:
                parsed = json.loads(raw_json)
                for item in parsed:
                    tc_res = TestCaseResult(
                        test_index=item.get("test_index", 1),
                        description=item.get("description"),
                        expected=item.get("expected"),
                        actual=item.get("actual"),
                        passed=bool(item.get("passed", False)),
                        error=item.get("error")
                    )
                    test_results.append(tc_res)
                    if tc_res.passed:
                        tests_passed += 1
                total_tests = len(test_results)
            except Exception as e:
                stderr_str += f"\nFailed parsing test case results: {e}"

        all_passed = (total_tests > 0 and tests_passed == total_tests)

        return SandboxExecutionResult(
            language=language,
            success=success and (not stderr_str or "Traceback" not in stderr_str),
            all_passed=all_passed,
            tests_passed=tests_passed,
            total_tests=total_tests,
            test_results=test_results,
            stdout=clean_stdout,
            stderr=stderr_str.strip(),
            execution_time_ms=round(elapsed_ms, 2)
        )

    @classmethod
    def _execute_sql(
        cls,
        code: str,
        test_cases: Optional[List[Dict[str, Any]]],
        custom_input: Optional[str]
    ) -> SandboxExecutionResult:
        import sqlite3
        start_time = time.time()

        if not test_cases:
            try:
                conn = sqlite3.connect(":memory:")
                cursor = conn.cursor()
                if custom_input:
                    cursor.executescript(custom_input)
                cursor.execute(code.strip().rstrip(";"))
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                formatted_rows = [list(r) for r in rows]
                conn.close()
                elapsed_ms = (time.time() - start_time) * 1000
                stdout = f"Columns: {cols}\nReturned {len(rows)} row(s):\n" + "\n".join(str(r) for r in formatted_rows[:20])
                return SandboxExecutionResult(
                    language="sql",
                    success=True,
                    all_passed=True,
                    tests_passed=1,
                    total_tests=1,
                    test_results=[TestCaseResult(test_index=0, description="Execute Query", passed=True, actual=formatted_rows)],
                    stdout=stdout,
                    execution_time_ms=round(elapsed_ms, 2)
                )
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                return SandboxExecutionResult(
                    language="sql",
                    success=False,
                    all_passed=False,
                    tests_passed=0,
                    total_tests=1,
                    test_results=[TestCaseResult(test_index=0, description="Execute Query", passed=False, error=str(e))],
                    stderr=str(e),
                    execution_time_ms=round(elapsed_ms, 2),
                    error_message=str(e)
                )

        test_results = []
        tests_passed = 0
        all_stdout = []
        all_stderr = []

        for idx, tc in enumerate(test_cases):
            desc = tc.get("description", f"Test Case {idx + 1}")
            setup_sql = tc.get("setup_sql") or tc.get("schema") or tc.get("input_data") or ""
            expected = tc.get("expected_output")

            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()
            try:
                # Execute setup table schema / seed rows
                if isinstance(setup_sql, str) and setup_sql.strip():
                    cursor.executescript(setup_sql)
                elif isinstance(setup_sql, list):
                    for stmt in setup_sql:
                        if isinstance(stmt, str):
                            cursor.executescript(stmt)

                # Clean and execute candidate SQL query
                clean_query = code.strip().rstrip(";")
                cursor.execute(clean_query)
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                formatted_rows = [list(r) for r in rows]

                # Evaluate correctness against expected output
                passed = False
                if expected is None:
                    passed = True
                elif isinstance(expected, int):
                    passed = (len(rows) == expected)
                elif isinstance(expected, list):
                    expected_normalized = [list(r) if isinstance(r, (list, tuple)) else r for r in expected]
                    passed = (formatted_rows == expected_normalized)
                    if not passed and len(formatted_rows) == len(expected_normalized):
                        passed = (str(formatted_rows).lower() == str(expected_normalized).lower())
                else:
                    passed = (formatted_rows == expected)

                if passed:
                    tests_passed += 1

                test_results.append(TestCaseResult(
                    test_index=idx,
                    description=desc,
                    expected=expected,
                    actual=formatted_rows,
                    passed=passed,
                    error=None if passed else f"Expected: {expected}, got: {formatted_rows}"
                ))
                all_stdout.append(f"✓ [{desc}] Passed: {passed} | {len(rows)} row(s): {formatted_rows[:3]}")
            except Exception as e:
                test_results.append(TestCaseResult(
                    test_index=idx,
                    description=desc,
                    expected=expected,
                    actual=None,
                    passed=False,
                    error=str(e)
                ))
                all_stderr.append(f"✗ [{desc}] SQL Error: {str(e)}")
            finally:
                conn.close()

        elapsed_ms = (time.time() - start_time) * 1000
        all_passed = (len(test_cases) > 0 and tests_passed == len(test_cases))

        return SandboxExecutionResult(
            language="sql",
            success=(len(all_stderr) == 0 or tests_passed > 0),
            all_passed=all_passed,
            tests_passed=tests_passed,
            total_tests=len(test_cases),
            test_results=test_results,
            stdout="\n".join(all_stdout),
            stderr="\n".join(all_stderr),
            execution_time_ms=round(elapsed_ms, 2),
            error_message=all_stderr[0] if all_stderr and not all_passed else None
        )
