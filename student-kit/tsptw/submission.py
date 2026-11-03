"""Static checks applied to an uploaded ``algorithm.py`` (same code on the
server and in ``check_submission.py``).

Allowed imports: the Python standard library except the modules in
``DENIED_MODULES``, plus ``numpy`` and ``tsptw``. Dynamic code execution
(``exec``, ``eval``, ``compile``, ``__import__``) is not allowed.
"""

from __future__ import annotations

import ast
import sys

MAX_BYTES = 256 * 1024
ALLOWED_THIRD_PARTY = frozenset({"numpy", "tsptw"})
ALLOWED_PRIVATE = frozenset({"__future__"})
DENIED_MODULES = frozenset(
    {
        # processes, threads, signals, native code
        "subprocess", "multiprocessing", "concurrent", "threading", "_thread",
        "signal", "ctypes", "pty", "resource", "importlib", "runpy", "code", "codeop",
        # network
        "socket", "ssl", "select", "selectors", "asyncio", "http", "urllib", "ftplib",
        "smtplib", "poplib", "imaplib", "xmlrpc", "socketserver", "webbrowser",
    }
)  # fmt: skip
DENIED_CALLS = frozenset({"exec", "eval", "compile", "__import__", "breakpoint"})


def _module_allowed(name: str) -> bool:
    top = name.split(".")[0]
    if top in ALLOWED_THIRD_PARTY or top in ALLOWED_PRIVATE:
        return True
    return top in sys.stdlib_module_names and top not in DENIED_MODULES and not top.startswith("_")


def check_source(source: str | bytes) -> list[str]:
    """Return a list of human-readable problems; an empty list means OK."""
    if isinstance(source, bytes):
        if len(source) > MAX_BYTES:
            return [f"file is larger than {MAX_BYTES // 1024} KB"]
        try:
            source = source.decode("utf-8")
        except UnicodeDecodeError:
            return ["file is not valid UTF-8"]
    elif len(source.encode("utf-8")) > MAX_BYTES:
        return [f"file is larger than {MAX_BYTES // 1024} KB"]

    try:
        tree = ast.parse(source, filename="algorithm.py")
    except SyntaxError as e:
        return [f"syntax error on line {e.lineno}: {e.msg}"]

    problems: list[str] = []
    solve = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "solve"), None
    )
    if solve is None:
        problems.append("missing top-level function: def solve(instance, time_limit, seed)")
    else:
        a = solve.args
        positional = len(a.posonlyargs) + len(a.args)
        if positional < 3 and a.vararg is None:
            problems.append("solve must accept three arguments: (instance, time_limit, seed)")
        elif positional - len(a.defaults) > 3:
            problems.append("solve must not require more than three arguments")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _module_allowed(alias.name):
                    problems.append(f"line {node.lineno}: import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                problems.append(f"line {node.lineno}: relative imports are not allowed (single file only)")
            elif node.module and not _module_allowed(node.module):
                problems.append(f"line {node.lineno}: import of '{node.module}' is not allowed")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in DENIED_CALLS:
                problems.append(f"line {node.lineno}: {node.func.id}() is not allowed")
    return problems
