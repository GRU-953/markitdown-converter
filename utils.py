"""
Shared utilities used by converter.py.
Kept in a separate module so they can be tested without importing the GUI stack.
"""

import re


def parse_dnd_paths(raw: str) -> list[str]:
    """
    Parse a tkinterdnd2 <<Drop>> event data string into a list of file paths.

    tkinterdnd2 encodes paths as space-separated tokens, with paths containing
    spaces wrapped in curly braces: ``/simple/path {/path with spaces/file.txt}``
    """
    paths = []
    for item in re.findall(r'\{[^}]*\}|\S+', raw):
        paths.append(item.strip("{}"))
    return paths
