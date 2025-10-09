import json
import statistics
import pathlib
from collections import defaultdict
from typing import DefaultDict, List

lat: DefaultDict[str, List[float]] = defaultdict(list)
counts: DefaultDict[str, int] = defaultdict(int)


path = pathlib.Path("data/metrics.log")
lat = defaultdict(list)
counts = defaultdict(int)
if path.exists():
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
            if rec.get("event") == "booking_attempt":
                counts["bookings_total"] += 1
                if rec.get("success"):
                    counts["bookings_success"] += 1
            elif "latency_ms" in rec:
                lat[rec.get("fn", "")].append(rec["latency_ms"])
        except Exception:
            pass


def stats(vals):
    if not vals:
        return "-"
    return f"avg {statistics.mean(vals):.1f} ms | p50 {statistics.median(vals):.1f} ms | p90 {statistics.quantiles(vals, n=10)[8]:.1f} ms"


print("Latency:")
for k, v in lat.items():
    print(f"  {k:>14}: {stats(v)}")
bt = counts["bookings_total"]
bs = counts["bookings_success"]
rate = (bs / bt * 100) if bt else 0
print(f"\nBooking completion: {bs}/{bt} = {rate:.1f}%")
