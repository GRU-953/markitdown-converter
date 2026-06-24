# v2 Design

## File structure
```
converter.py       — full app (replaces v1)
requirements.txt   — updated deps
build_exe.bat      — one-line PyInstaller command
```

## UI layout (CustomTkinter, dark/light aware)
```
+----------------------------------------------------------+
| MarkItDown Converter              [Light | Dark | System]|
+----------------------------------------------------------+
| [+ Add Files]  [Clear List]       (or drag files here)   |
| +------------------------------------------------------+ |
| | filename.docx        [pending]                       | |
| | report.pdf           [converted]                     | |
| | data.xlsx            [error: <msg>]                  | |
| +------------------------------------------------------+ |
| [Convert All]                                            |
+----------------------------------------------------------+
| [Raw Markdown]  [Preview]   <- CTkTabview                |
| +------------------------------------------------------+ |
| |  CTkTextbox (raw) OR HTMLScrolledText (preview)      | |
| +------------------------------------------------------+ |
| [Save Selected]  [Save All]                              |
+----------------------------------------------------------+
```

## Class: App(TkinterDnD.Tk)
Inherits TkinterDnD.Tk (not CTk directly) — required for DnD on Windows.
CTk widgets still usable inside a TkinterDnD root.

### State
- _files: list[dict]  — {path, status, result_text}
- _selected_idx: int  — which row is shown in output pane
- _md_engine: MarkItDown()
- _appearance: StringVar  — bound to the mode selector

### Key methods
- _build_ui()           — lay out all widgets
- _on_drop(event)       — parse event.data paths, call _add_files()
- _add_files(paths)     — append unique paths to _files, refresh list
- _convert_all()        — iterate _files, call MarkItDown for each, update status
- _select_row(idx)      — set _selected_idx, refresh output pane
- _refresh_list()       — redraw the file list rows
- _refresh_output()     — show raw or preview for _selected_idx
- _save_selected()      — save _files[_selected_idx].result_text
- _save_all()           — save all converted files
- _toggle_mode(mode)    — ctk.set_appearance_mode(mode)

## Drag & drop detail
TkinterDnD.Tk registers the root; bind "<Drop>" on a CTkFrame that fills
the file-list area. event.data on Windows is a space-separated list of
paths (braces around paths with spaces).

## Preview detail
- Raw tab:     CTkTextbox (read-only, monospace)
- Preview tab: HTMLScrolledText from tkhtmlview; on tab switch call
               html_widget.set_html(markdown.markdown(text))

## requirements.txt
markitdown
customtkinter
tkinterdnd2
markdown
tkhtmlview

## build_exe.bat
pyinstaller --onefile --windowed --name MarkItDownConverter converter.py