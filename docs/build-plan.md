# Build Plan

## Unit 1 — Complete app: converter.py + requirements.txt

### What to build
- requirements.txt  (one line: markitdown)
- converter.py      (full App class per design.md)

### Acceptance check
1. Syntax:   python -m py_compile converter.py   -> exit 0
2. Imports:  python -c "import tkinter, markitdown" -> exit 0
3. Smoke:    python -c "
   from markitdown import MarkItDown
   import tempfile, pathlib, textwrap
   tmp = pathlib.Path(tempfile.mktemp(suffix='.txt'))
   tmp.write_text('Hello world')
   result = MarkItDown().convert(str(tmp))
   assert result.text_content.strip(), 'empty output'
   tmp.unlink()
   print('smoke ok')
   "  -> prints 'smoke ok', exit 0

### Done signal
All three checks exit 0 -> unit DONE.
Any failure -> surfaces as a blocker for the fix phase.

## Notes
- App is ~65 lines; one unit is the right granularity (no artificial split).
- Headless smoke test avoids opening a real Tk window on a CI/build machine.
- MarkItDown must be installed before tests run: pip install -r requirements.txt