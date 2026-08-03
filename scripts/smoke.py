"""Cross-platform production smoke test for the single-process application."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def request(url: str, method: str = "GET") -> tuple[int, bytes]:
    operation = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(operation, timeout=5) as response:  # noqa: S310 - localhost only
        return response.status, response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = f"http://127.0.0.1:{arguments.port}"
    with tempfile.TemporaryDirectory(prefix="ipa-smoke-") as data_directory:
        environment = os.environ.copy()
        environment["INTUNE_AUDITOR_DATA_DIR_OVERRIDE"] = data_directory
        process = subprocess.Popen(  # noqa: S603 - fixed interpreter/module/arguments
            [
                sys.executable,
                "-m",
                "uvicorn",
                "intune_auditor.main:app",
                "--app-dir",
                str(root / "backend"),
                "--host",
                "127.0.0.1",
                "--port",
                str(arguments.port),
            ],
            cwd=root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            for _ in range(120):
                if process.poll() is not None:
                    break
                try:
                    status, _ = request(f"{base}/api/v1/health")
                    if status == 200:
                        break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.25)
            else:
                raise RuntimeError("health_timeout")
            health_status, health_body = request(f"{base}/api/v1/health")
            frontend_status, frontend_body = request(base)
            demo_status, demo_body = request(f"{base}/api/v1/audits/demo?language=en", "POST")
            health = json.loads(health_body)
            demo = json.loads(demo_body)
            if health_status != 200 or health["data"]["status"] != "ok":
                raise RuntimeError("health_failed")
            if frontend_status != 200 or b'<div id="root"></div>' not in frontend_body:
                raise RuntimeError("frontend_failed")
            if demo_status != 201 or len(demo["data"]["policies"]) < 1:
                raise RuntimeError("demo_failed")
            report_status, report_body = request(
                f"{base}/api/v1/audits/{demo['data']['audit_id']}/reports/html?language=en"
            )
            if report_status != 200 or b"Intune Policy Auditor" not in report_body:
                raise RuntimeError("report_failed")
            print("production smoke passed")
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            if process.returncode not in {0, -15, 15, 143, 1}:
                output = process.stdout.read() if process.stdout else ""
                print(output, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
