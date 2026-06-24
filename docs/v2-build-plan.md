# v2 Build Plan

## Unit 1 — converter.py (full v2 rewrite) + requirements.txt + build_exe.bat

### Acceptance checks
1. python -m py_compile converter.py                        -> exit 0
2. pip install -r requirements.txt -q                       -> exit 0
3. python -c "import customtkinter, tkinterdnd2, markdown, tkhtmlview, markitdown; print('imports ok')"  -> exit 0
4. Smoke: convert a .txt file headlessly, assert non-empty result  -> exit 0
5. PyInstaller build: pyinstaller --onefile --windowed --name MarkItDownConverter converter.py  -> exit 0 and dist/MarkItDownConverter.exe exists