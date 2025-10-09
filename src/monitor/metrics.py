from __future__ import annotations
import time
import json
import os

LOG_PATH = "data/metrics.log"


def timed(fn, *a, **kw):
    t0 = time.time()
    out = fn(*a, **kw)
    dt_ms = (time.time() - t0) * 1000.0
    os.makedirs("data", exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps({"fn": fn.__name__, "latency_ms": round(dt_ms, 2)}) + "\n")
    return out, dt_ms


def log_event(name: str, **fields):
    os.makedirs("data", exist_ok=True)
    rec = {"event": name, **fields}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")
