import os
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
    assert res.security_clean is True
    assert res.network_egress_blocked is True
    assert res.resource_limits_enforced is True

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
    assert res.security_clean is True

# =====================================================================
# Google Tier-1 Security Guardrail Tests
# =====================================================================

def test_sandbox_security_blocks_forbidden_modules():
    """Verifies that malicious imports (ctypes, subprocess, pty) are stopped pre-flight."""
    malicious_codes = [
        "import subprocess\ndef solution(): subprocess.run(['ls'])",
        "from ctypes import CDLL\ndef solution(): pass",
        "import pty\ndef solution(): pty.spawn('/bin/sh')"
    ]
    for code in malicious_codes:
        res = SandboxService.execute_code("python", code)
        assert res.success is False
        assert res.security_clean is False
        assert len(res.security_violations) > 0
        assert "Security Policy Violation" in (res.error_message or "")

def test_sandbox_security_blocks_dangerous_system_calls():
    """Verifies that dangerous OS calls like os.system or os.fork are stopped."""
    dangerous_codes = [
        "import os\ndef solution(): os.system('cat /etc/passwd')",
        "import os\ndef solution(): os.fork()",
        "import os\ndef solution(): os.kill(1, 9)"
    ]
    for code in dangerous_codes:
        res = SandboxService.execute_code("python", code)
        assert res.success is False
        assert res.security_clean is False
        assert "Forbidden system" in (res.error_message or "")

def test_sandbox_security_blocks_sensitive_file_paths():
    """Verifies that attempts to reference .env, id_rsa, or /etc/shadow are blocked."""
    code = """
def solution():
    with open('/etc/passwd') as f:
        return f.read()
"""
    res = SandboxService.execute_code("python", code)
    assert res.success is False
    assert res.security_clean is False
    assert any("/etc/passwd" in v for v in res.security_violations)

def test_sandbox_zero_egress_network_isolation():
    """Verifies that network socket creation in runtime is physically denied."""
    code = """
import socket
def solution():
    s = socket.socket()
    s.connect(('1.1.1.1', 80))
"""
    test_cases = [{"input_data": [], "expected_output": None}]
    res = SandboxService.execute_code("python", code, test_cases)
    assert res.all_passed is False
    # Verify socket was blocked by our injected zero-egress network guard
    err_text = (res.test_results[0].error or "").lower() if res.test_results else ""
    assert "egress network access denied" in err_text or "permissionerror" in err_text

def test_sandbox_environment_sanitization_no_secrets_leak():
    """Verifies that host secrets (e.g. mock DB credentials) are NOT present in sandbox process."""
    os.environ["SECRET_ENTERPRISE_TOKEN"] = "ultra_confidential_98765"
    code = """
import os
def solution():
    return os.environ.get('SECRET_ENTERPRISE_TOKEN', 'SAFE_NOT_FOUND')
"""
    test_cases = [{"input_data": [], "expected_output": "SAFE_NOT_FOUND"}]
    res = SandboxService.execute_code("python", code, test_cases)
    assert res.success is True
    assert res.all_passed is True
    assert res.test_results[0].actual == "SAFE_NOT_FOUND"

def test_sandbox_javascript_security_blocks_child_process():
    """Verifies that Node.js child_process and cluster invocations are blocked."""
    malicious_js = """
const cp = require('child_process');
function solution() {
    cp.execSync('whoami');
}
"""
    res = SandboxService.execute_code("javascript", malicious_js)
    assert res.success is False
    assert res.security_clean is False
    assert any("child_process" in v for v in res.security_violations)
