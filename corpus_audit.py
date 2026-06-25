"""
Full corpus audit — tests one representative file per extension from D:/Test_files.
Outputs a pass/fail/empty table so we know exactly what needs fixing.
"""
import sys, os, io, time, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

from pipeline import convert_file

TEST_ROOT = pathlib.Path(r"D:/Test_files")

# Collect one sample per extension (pick shortest file for speed)
samples = {}
SKIP_EXTS = {"", ".gitignore", ".ds_store", ".tmp", ".lnk", ".bak"}
SKIP_NAME_PREFIXES = ("~$", "._", ".~")  # temp locks and macOS resource forks

for f in TEST_ROOT.rglob("*"):
    if not f.is_file():
        continue
    if any(f.name.startswith(p) for p in SKIP_NAME_PREFIXES):
        continue
    ext = f.suffix.lower()
    if ext in SKIP_EXTS:
        continue
    if ext not in samples or f.stat().st_size < samples[ext].stat().st_size:
        samples[ext] = f

# Sort by extension name
results = []
for ext in sorted(samples):
    f = samples[ext]
    kb = round(f.stat().st_size / 1024, 1)
    t0 = time.time()
    try:
        r = convert_file(str(f), auto_ocr=True, auto_bijoy=True)
        text = r["text"]
        words = len(text.split()) if text else 0
        elapsed = round(time.time() - t0, 2)
        if words > 0:
            status = "PASS"
        else:
            status = "EMPTY"
        results.append((status, ext, kb, elapsed, r["steps"], words, f.name, ""))
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        results.append(("FAIL", ext, kb, elapsed, [], 0, f.name, str(e)[:100]))

# Print table
PASS = sum(1 for r in results if r[0] == "PASS")
EMPTY = sum(1 for r in results if r[0] == "EMPTY")
FAIL = sum(1 for r in results if r[0] == "FAIL")

print(f"\n{'Status':<6} {'Ext':<8} {'KB':>6} {'Sec':>5}  {'Steps':<20} {'Words':>6}  {'File'}")
print("-" * 95)
for status, ext, kb, elapsed, steps, words, name, err in results:
    step_str = "+".join(steps) if steps else "-"
    flag = "  " + err[:60] if status == "FAIL" else ""
    print(f"{status:<6} {ext:<8} {kb:>6} {elapsed:>5}  {step_str:<20} {words:>6}  {name[:50]}{flag}")

print()
print(f"SUMMARY: {PASS} PASS  |  {EMPTY} EMPTY  |  {FAIL} FAIL  (total {len(results)} types)")
sys.exit(0 if FAIL == 0 and EMPTY == 0 else 1)
