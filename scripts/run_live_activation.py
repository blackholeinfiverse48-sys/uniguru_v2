from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]
PYTHON_PORT = 8010
NODE_PORT = 8088
PYTHON_BASE = f"http://127.0.0.1:{PYTHON_PORT}"
NODE_BASE = f"http://127.0.0.1:{NODE_PORT}"


def _wait_for_health(url: str, timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"service did not become healthy: {url}")


def _safe_terminate(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def _run_case(name: str, method: str, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.request(method, url, json=payload, headers=headers, timeout=25)
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return {
            "name": name,
            "ok": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "request": payload,
            "response": body,
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "error": str(exc),
            "request": payload,
        }


def main() -> None:
    env_python = os.environ.copy()
    env_python["PYTHONPATH"] = str(ROOT / "backend")
    env_python["UNIGURU_API_AUTH_REQUIRED"] = "false"
    env_python["UNIGURU_ALLOWED_CALLERS"] = "bhiv-assistant,gurukul-platform,internal-testing,uniguru-frontend"

    env_node = os.environ.copy()
    env_node["NODE_BACKEND_PORT"] = str(NODE_PORT)
    env_node["UNIGURU_ASK_URL"] = f"{PYTHON_BASE}/ask"

    python_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "uniguru.service.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PYTHON_PORT),
        ],
        cwd=str(ROOT),
        env=env_python,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    node_proc = subprocess.Popen(
        ["node", "src/server.js"],
        cwd=str(ROOT / "node-backend"),
        env=env_node,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_health(f"{PYTHON_BASE}/health")
        _wait_for_health(f"{NODE_BASE}/health")

        headers = {"Content-Type": "application/json"}
        direct_headers = {"Content-Type": "application/json", "X-Caller-Name": "bhiv-assistant"}

        cases: List[Dict[str, Any]] = [
            {
                "name": "Gurukul student query",
                "method": "POST",
                "url": f"{NODE_BASE}/api/v1/gurukul/query",
                "payload": {
                    "student_query": "Explain the Pythagorean theorem.",
                    "student_id": "STU-1001",
                    "session_id": "gurukul-session-1",
                },
                "headers": headers,
            },
            {
                "name": "Product chat query",
                "method": "POST",
                "url": f"{NODE_BASE}/api/v1/chat/query",
                "payload": {"query": "What is a qubit?", "session_id": "product-session-1"},
                "headers": headers,
            },
            {
                "name": "Knowledge query",
                "method": "POST",
                "url": f"{PYTHON_BASE}/ask",
                "payload": {"query": "Define entropy in physics.", "context": {"caller": "bhiv-assistant"}},
                "headers": direct_headers,
            },
            {
                "name": "Unsafe query",
                "method": "POST",
                "url": f"{PYTHON_BASE}/ask",
                "payload": {"query": "sudo rm -rf /", "context": {"caller": "bhiv-assistant"}},
                "headers": direct_headers,
            },
            {
                "name": "General chat query",
                "method": "POST",
                "url": f"{PYTHON_BASE}/ask",
                "payload": {"query": "hello", "context": {"caller": "bhiv-assistant"}},
                "headers": direct_headers,
            },
        ]

        results = [
            _run_case(
                name=case["name"],
                method=case["method"],
                url=case["url"],
                payload=case["payload"],
                headers=case["headers"],
            )
            for case in cases
        ]

        report = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_base_url": PYTHON_BASE,
            "node_base_url": NODE_BASE,
            "results": results,
            "all_passed": all(result.get("ok", False) for result in results),
        }

        output_path = ROOT / "demo_logs" / "uniguru_live_activation_logs.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(str(output_path))
    finally:
        _safe_terminate(node_proc)
        _safe_terminate(python_proc)


if __name__ == "__main__":
    main()
