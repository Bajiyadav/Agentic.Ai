import pytest
from src.services.sandbox_service import SandboxService

def test_sandbox_python_addition():
    code = """
def solution(a, b):
    return a + b
"""
    test_cases = [
        {"input_data": [2, 3], "expected_output": 5, "description": "2 + 3 = 5"},
        {"input_data": [-1, 1], "expected_output": 0, "description": "-1 + 1 = 0"}
    ]
    res = SandboxService.execute_code("python", code, test_cases)
    assert res.success is True
    assert res.all_passed is True
    assert res.tests_passed == 2
    assert res.total_tests == 2
    assert len(res.test_results) == 2
    assert res.test_results[0].passed is True
    assert res.test_results[1].passed is True

def test_sandbox_python_partial_failure():
    code = """
def solution(a, b):
    return a * b  # Intentional bug
"""
    test_cases = [
        {"input_data": [2, 2], "expected_output": 4, "description": "2 * 2 = 4 (luckily matches)"},
        {"input_data": [2, 3], "expected_output": 5, "description": "2 * 3 != 5 (should fail)"}
    ]
    res = SandboxService.execute_code("python", code, test_cases)
    assert res.all_passed is False
    assert res.tests_passed == 1
    assert res.total_tests == 2
    assert res.test_results[0].passed is True
    assert res.test_results[1].passed is False

def test_sandbox_python_timeout_protection():
    code = """
import time
def solution():
    while True:
        pass
"""
    test_cases = [{"input_data": [], "expected_output": None}]
    res = SandboxService.execute_code("python", code, test_cases)
    assert res.all_passed is False
    assert "timed out" in (res.error_message or "").lower()

def test_sandbox_javascript_execution():
    code = """
function solution(numbers) {
    return numbers.reduce((acc, x) => acc + x, 0);
}
"""
    test_cases = [
        {"input_data": [[1, 2, 3, 4]], "expected_output": 10, "description": "Sum 1..4"}
    ]
    res = SandboxService.execute_code("javascript", code, test_cases)
    assert res.success is True
    assert res.all_passed is True
    assert res.tests_passed == 1
