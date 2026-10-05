import time
import requests
import psutil
import subprocess
import csv

URL = "http://127.0.0.1:5000/v1/chat/completions"
PROMPT = "Explain what photosynthesis is in simple terms."

TEXTGEN_PID = -1  #kiekviena serverio paleidima naujas

WARMUP = 5
CALLS = 50
TIMEOUT = 120

def get_ram_mb():
    process = psutil.Process(TEXTGEN_PID)
    return process.memory_info().rss / (1024 ** 2)

def get_vram_mb():
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits"
        ],
        capture_output=True,
        text=True,
        check=True
    )

    values = []

    for line in result.stdout.splitlines():
        line = line.strip()

        if line and line != "[N/A]":
            values.append(float(line))

    if not values:
        raise RuntimeError("!!! nepavyko gauti VRAM naudojimo duomenu")

    return sum(values)

def make_request(session):
    jsonp = {
        "messages": [
            {"role": "user", "content": PROMPT}
        ],
        "max_tokens": 512
    }

    return session.post(
        URL,
        json=jsonp,
        timeout=TIMEOUT
    )

with requests.Session() as session:

    print("--- APSILIMAS ---")
    for i in range(WARMUP):
        response = make_request(session)
        response.raise_for_status()

        print(f"Apsilimo užklausa {i + 1}/{WARMUP}")

    ram_start = get_ram_mb()
    vram_start = get_vram_mb()

    max_ram = ram_start
    max_vram = vram_start

    results = []

    ram_new_max_count = 0
    vram_new_max_count = 0

    print("\n--- MATAVIMAI ---")
    for i in range(CALLS):

        t0 = time.perf_counter()

        response = make_request(session)
        response.raise_for_status()

        elapsed_ms = (time.perf_counter() - t0) * 1000

        ram = get_ram_mb()
        vram = get_vram_mb()

        if ram > max_ram:
            ram_new_max = True
            ram_new_max_count += 1
            max_ram = ram
        else:
            ram_new_max = False

        if vram > max_vram:
            vram_new_max = True
            vram_new_max_count += 1
            max_vram = vram
        else:
            vram_new_max = False

        results.append({
            "request": i + 1,
            "time_ms": elapsed_ms,
            "ram_mb": ram,
            "vram_mb": vram,
            "ram_new_max": ram_new_max,
            "vram_new_max": vram_new_max,
            "ram_max_mb": max_ram,
            "vram_max_mb": max_vram
        })

        print(
            f"{i + 1:02d}: "
            f"{elapsed_ms:.0f} ms | "
            f"RAM {ram:.1f} MB "
            f"{'↑  ' if ram_new_max else '   '} | "
            f"VRAM {vram:.1f} MB "
            f"{'↑  ' if vram_new_max else '   '}"
        )

ram_end = results[-1]["ram_mb"]
vram_end = results[-1]["vram_mb"]

ram_growth = ram_end - ram_start
vram_growth = vram_end - vram_start

ram_peak_growth = max_ram - ram_start
vram_peak_growth = max_vram - vram_start

ram_new_max_percent = (ram_new_max_count / CALLS * 100)
vram_new_max_percent = (vram_new_max_count / CALLS * 100)

print("\n--- REZULTATAI ---")
print(f"RAM pradzia:                    {ram_start:.1f} MB")
print(f"RAM pabaiga:                    {ram_end:.1f} MB")
print(f"RAM pokytis:                    {ram_growth:.1f} MB")
print(f"RAM didziausias pokytis:        {ram_peak_growth:.1f} MB")
print(
    f"RAM nauju maksimumu:            "
    f"{ram_new_max_count}/{CALLS} "
    f"({ram_new_max_percent:.1f}%)"
)
print()

print(f"VRAM pradzia:                   {vram_start:.1f} MB")
print(f"VRAM pabaiga:                   {vram_end:.1f} MB")
print(f"VRAM pokytis:                   {vram_growth:.1f} MB")
print(f"VRAM didziausias pokytis:       {vram_peak_growth:.1f} MB")
print(
    f"VRAM nauju maksimumu:           "
    f"{vram_new_max_count}/{CALLS} "
    f"({vram_new_max_percent:.1f}%)"
)

with open("memory_test.csv", "w", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "request",
            "time_ms",
            "ram_mb",
            "vram_mb",
            "ram_new_max",
            "vram_new_max",
            "ram_max_mb",
            "vram_max_mb"
        ]
    )

    writer.writeheader()
    writer.writerows(results)