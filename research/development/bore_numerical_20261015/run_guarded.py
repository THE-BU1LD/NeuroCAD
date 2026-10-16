"""Retain bounded single-process maintenance checks and failures; no native workloads."""
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
name, *command = sys.argv[1:]
if not command or not name.replace("-", "").replace("_", "").isalnum():
    raise SystemExit("Provide a unique receipt name followed by the command")
receipt = out / (name + ".json")
if receipt.exists():
    raise SystemExit("Refusing to overwrite a retained receipt")
env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1",
           OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
start = time.monotonic()
peak, stop = 0.0, None
with (out / (name + ".log")).open("x") as log:
    child = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True)
    while child.poll() is None:
        sample = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)], capture_output=True, text=True)
        if sample.returncode != 0 or not sample.stdout.strip():
            stop = "rss_monitor_unavailable"
            os.killpg(child.pid, signal.SIGTERM)
            break
        if sample.stdout.strip():
            peak = max(peak, float(sample.stdout.strip()) / 1024)
        if peak > 96 or time.monotonic() - start > 20:
            stop = "memory_limit" if peak > 96 else "time_limit"
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
            break
        time.sleep(0.05)
    code = child.wait()
result = {"command": command, "exit_code": code, "guard_stop": stop,
          "wall_seconds": time.monotonic() - start, "sampled_peak_rss_mib": peak,
          "child_peak_rss_mib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / (1048576 if sys.platform == "darwin" else 1024),
          "environment": {"platform": platform.platform(), "thread_limit": 1},
          "source_hashes": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for folder in ("core", "tests") for p in sorted((root/folder).rglob("*.py"))}}
receipt.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k:v for k,v in result.items() if k != "source_hashes"}, indent=2))
print((out / (name + ".log")).read_text()[-2500:])
raise SystemExit(124 if stop else code)
