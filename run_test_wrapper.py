
import subprocess
import sys

def run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_conversation_router.py"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    print("RETURN CODE:", result.returncode)

if __name__ == "__main__":
    run_tests()
