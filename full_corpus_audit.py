"""
Full corpus audit — every file in D:/Test_files tested against the live pipeline.
Outputs a summary table + JSON results file for automated analysis.

Usage:
    python full_corpus_audit.py [--no-ocr] [--workers N] [--out results.json]
"""
import sys, os, io, json, time, pathlib, argparse, signal
import concurrent.futures

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

from pipeline import convert_file, is_unsupported

TEST_ROOT = pathlib.Path("D:/Test_files")
SKIP_NAME_PREFIXES = ("~$", "._", ".~")
SKIP_EXTS = {".tmp", ".ds_store", ".lnk", ".bak", ""}
TIMEOUT_SEC = 45


def _classify_file(f: pathlib.Path, auto_ocr: bool) -> dict:
    """Return a result dict for a single file."""
    ext = f.suffix.lower()
    kb = round(f.stat().st_size / 1024, 1)
    t0 = time.time()
    try:
        r = convert_file(str(f), auto_ocr=auto_ocr, auto_bijoy=True)
        text = r.get("text", "")
        words = len(text.split()) if text else 0
        elapsed = round(time.time() - t0, 2)
        if words > 0:
            status = "PASS"
        elif is_unsupported(f):
            # Should have raised — shouldn't reach here
            status = "UNSUPPORTED"
        else:
            status = "EMPTY"
        return {"status": status, "ext": ext, "kb": kb, "elapsed": elapsed,
                "steps": r.get("steps", []), "words": words,
                "file": str(f), "name": f.name, "error": ""}
    except ValueError as exc:
        elapsed = round(time.time() - t0, 2)
        msg = str(exc)
        status = "UNSUPPORTED" if ("unsupported format" in msg.lower() or
                                    "no text can be extracted" in msg.lower()) else "FAIL"
        return {"status": status, "ext": ext, "kb": kb, "elapsed": elapsed,
                "steps": [], "words": 0, "file": str(f), "name": f.name, "error": msg}
    except Exception as exc:
        elapsed = round(time.time() - t0, 2)
        return {"status": "FAIL", "ext": ext, "kb": kb, "elapsed": elapsed,
                "steps": [], "words": 0, "file": str(f), "name": f.name,
                "error": str(exc)[:200]}


def _safe_convert(args):
    f, auto_ocr, file_timeout = args
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as inner:
            fut = inner.submit(_classify_file, f, auto_ocr)
            try:
                return fut.result(timeout=file_timeout)
            except concurrent.futures.TimeoutError:
                return {"status": "FAIL", "ext": f.suffix.lower(),
                        "kb": round(f.stat().st_size / 1024, 1), "elapsed": file_timeout,
                        "steps": [], "words": 0, "file": str(f), "name": f.name,
                        "error": f"Timeout after {file_timeout}s"}
    except Exception as exc:
        return {"status": "FAIL", "ext": f.suffix.lower(), "kb": 0, "elapsed": 0,
                "steps": [], "words": 0, "file": str(f), "name": f.name,
                "error": f"Unhandled: {exc}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ocr", action="store_true", help="Skip OCR (faster)")
    ap.add_argument("--workers", type=int, default=4, help="Parallel workers")
    ap.add_argument("--out", default="full_audit_results.json", help="JSON output path")
    ap.add_argument("--file-timeout", type=int, default=30, help="Per-file timeout in seconds")
    args = ap.parse_args()

    auto_ocr = not args.no_ocr

    # Collect all files
    all_files = []
    for f in TEST_ROOT.rglob("*"):
        if not f.is_file():
            continue
        if any(f.name.startswith(p) for p in SKIP_NAME_PREFIXES):
            continue
        if f.suffix.lower() in SKIP_EXTS or f.name.lower() in (".ds_store",):
            continue
        all_files.append(f)

    total = len(all_files)
    print(f"\nFull corpus audit — {total} files, {args.workers} workers, ocr={'on' if auto_ocr else 'off'}")
    print("=" * 80)

    results = []
    done = 0
    t_start = time.time()

    file_timeout = args.file_timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_safe_convert, (f, auto_ocr, file_timeout)): f for f in all_files}
        for fut in concurrent.futures.as_completed(futures, timeout=file_timeout * total + 120):
            r = fut.result()
            results.append(r)
            done += 1
            if done % 50 == 0 or done == total:
                elapsed = round(time.time() - t_start, 1)
                print(f"  [{done}/{total}] {elapsed}s elapsed …", flush=True)

    # Write JSON
    out_path = pathlib.Path(args.out)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Summary ──────────────────────────────────────────────────────────────
    by_status: dict[str, list] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    print(f"\n{'Status':<12} {'Count':>6}  {'Ext distribution (top 8)'}")
    print("-" * 78)
    for st in ("PASS", "EMPTY", "UNSUPPORTED", "FAIL"):
        group = by_status.get(st, [])
        if not group:
            continue
        from collections import Counter
        top = Counter(r["ext"] for r in group).most_common(8)
        ext_str = "  ".join(f"{e}×{c}" for e, c in top)
        print(f"{st:<12} {len(group):>6}  {ext_str}")

    # Show FAIL details
    fails = by_status.get("FAIL", [])
    if fails:
        print(f"\nFAIL detail ({len(fails)} files):")
        from collections import Counter
        err_groups: dict[str, list] = {}
        for r in fails:
            key = r["error"][:80]
            err_groups.setdefault(key, []).append(r["ext"])
        for msg, exts in sorted(err_groups.items(), key=lambda x: -len(x[1])):
            cnt_by_ext = Counter(exts)
            print(f"  [{len(exts)}]  {msg[:70]}")
            print(f"        {dict(cnt_by_ext)}")

    # Show EMPTY details
    empties = by_status.get("EMPTY", [])
    if empties:
        from collections import Counter
        print(f"\nEMPTY detail ({len(empties)} files — converted but no text extracted):")
        for ext, cnt in Counter(r["ext"] for r in empties).most_common():
            print(f"  {ext}: {cnt}")

    total_time = round(time.time() - t_start, 1)
    pass_c = len(by_status.get("PASS", []))
    empty_c = len(by_status.get("EMPTY", []))
    unsup_c = len(by_status.get("UNSUPPORTED", []))
    fail_c = len(by_status.get("FAIL", []))
    fixable = pass_c + empty_c + fail_c  # excludes genuinely unsupported
    print(f"\nSUMMARY: {pass_c} PASS  |  {empty_c} EMPTY  |  {unsup_c} UNSUPPORTED  |  {fail_c} FAIL")
    print(f"Fixable pass rate: {pass_c}/{fixable} = {100*pass_c//max(fixable,1)}%")
    print(f"Total time: {total_time}s  |  Results: {out_path}")
    sys.exit(0 if fail_c == 0 else 1)


if __name__ == "__main__":
    main()
