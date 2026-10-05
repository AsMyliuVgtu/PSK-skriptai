import time
import requests
from statistics import quantiles

URL = "http://127.0.0.1:5000/v1/models"
WARMUP=3
CALLS=30

with requests.Session() as session:
    times = []

    for i in range(WARMUP + CALLS):
        t0 = time.perf_counter()
        request = session.get(URL, timeout=5)
        request.raise_for_status()

        ms = (time.perf_counter() - t0) * 1000

        if i >= WARMUP:
            times.append(ms)

p95 = quantiles(times, n=100)[94]
print(f"p95: {p95:.2f} ms")