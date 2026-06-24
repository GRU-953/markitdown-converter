import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

try:
    from markitdown import MarkItDown
except ImportError:
    _r = tk.Tk()
    _r.withdraw()
    messagebox.showerror("MarkItDown not found", "Run:  pip install markitdown")
    sys.exit(1)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MarkItDown Converter")
        self.minsize(600, 420)
        self._path = tk.StringVar(value="No file selected")
        self._md = MarkItDown()
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

        ttk.Button(self, text="Open File…", command=self._open).grid(
            row=0, column=0, padx=8, pady=(10, 4), sticky="w"
        )
        ttk.Label(self, textvariable=self._path, anchor="w").grid(
            row=0, column=1, padx=(0, 8), pady=(10, 4), sticky="ew"
        )
        ttk.Button(self, text="Convert", command=self._convert).grid(
            row=1, column=0, padx=8, pady=4, sticky="w"
        )
        ttk.Label(self, text="Markdown Output:").grid(
            row=2, column=0, columnspan=2, padx=8, pady=(8, 2), sticky="w"
        )
        self._out = scrolledtext.ScrolledText(self, wrap=tk.WORD, state=tk.DISABLED)
        self._out.grid(row=3, column=0, columnspan=2, padx=8, pady=4, sticky="nsew")
        ttk.Button(self, text="Save as .md…", command=self._save).grid(
            row=4, column=0, padx=8, pady=(4, 10), sticky="w"
        )

    def _open(self):
        p = filedialog.askopenfilename(
            title="Select a file to convert",
            filetypes=[
                ("Supported", "*.pdf *.docx *.xlsx *.pptx *.html *.htm *.txt *.csv *.json *.xml *.zip"),
                ("All files", "*.*"),
            ],
        )
        if p:
            self._path.set(p)

    def _convert(self):
        p = self._path.get()
        if p == "No file selected":
            messagebox.showinfo("No file", "Open a file first.")
            return
        try:
            text = self._md.convert(p).text_content or ""
        except Exception as exc:
            messagebox.showerror("Conversion failed", str(exc))
            return
        self._out.config(state=tk.NORMAL)
        self._out.delete("1.0", tk.END)
        self._out.insert("1.0", text)
        self._out.config(state=tk.DISABLED)

    def _save(self):
        text = self._out.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Nothing to save", "Convert a file first.")
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if p:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)


if __name__ == "__main__":
    App().mainloop()