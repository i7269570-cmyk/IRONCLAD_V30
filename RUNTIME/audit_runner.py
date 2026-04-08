# RUNTIME/audit_runner.py

import subprocess

def run_audit():
    result = subprocess.run(
        ["python", "tests/test_structure.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError("AUDIT_FAIL")
    
    print("AUDIT_PASS")

if __name__ == "__main__":
    run_audit()