# Brainstorm — v2

## What is being added (all five explicitly requested)
1. Drag & drop  — drop files directly onto the app instead of using Open dialog
2. Batch conversion  — process a list of multiple files in one go
3. Markdown preview  — embedded pane that renders the output as formatted HTML
4. Dark mode  — toggle between light / dark / system appearance
5. .exe packaging  — standalone Windows executable via PyInstaller

## Why each feature now (override of v1 YAGNI)
User explicitly requested all five after v1 shipped. Each is a clear, bounded,
testable addition. No feature here requires the others, but they compose well.

## Tech stack (smallest-correct per feature)
- UI base:      customtkinter  — replaces plain tkinter; dark/light mode is built in
- Drag & drop:  tkinterdnd2    — standard DnD extension for tk/ctk on Windows
- MD preview:   markdown + tkhtmlview  — markdown converts .text_content to HTML;
                tkhtmlview renders it inside the window
- Batch:        CTkScrollableFrame with per-file rows; no extra library needed
- Packaging:    pyinstaller (build-time only, not a runtime dep)

## New requirements.txt
markitdown
customtkinter
tkinterdnd2
markdown
tkhtmlview

## build_exe.bat (one-liner packaging script)
pyinstaller --onefile --windowed --name MarkItDownConverter converter.py

## Acceptance items (minimum)
- [ ] Dropping a file onto the window adds it to the file list
- [ ] Add Files button still works (multi-select)
- [ ] Convert All converts every file in the list; per-row status updates
- [ ] Clicking a row in the list shows its Markdown in the output pane
- [ ] Preview tab renders the Markdown as formatted HTML (headings, bold, lists)
- [ ] Dark / Light / System toggle changes appearance without restart
- [ ] python -m py_compile converter.py exits 0
- [ ] pyinstaller build produces dist/MarkItDownConverter.exe