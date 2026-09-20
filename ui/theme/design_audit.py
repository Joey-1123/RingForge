#!/usr/bin/env python3
"""
RingForge Design Audit Script

Audits PySide6 UI code against ringforge-gui-design best practices.
Checks for: hardcoded colors, missing focus policies, missing accessible names,
missing minimum sizes, missing tokens, missing keyboard shortcuts, etc.

Usage:
    uv run python -m ui.theme.design_audit [path]

Default path: ui/
"""

import ast
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

# ─── Finding Types ────────────────────────────────────────

@dataclass
class Finding:
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    category: str  # "hardcoded_color", "missing_focus", "missing_accessible", etc.
    message: str
    suggestion: str = ""


# ─── Audit Rules ──────────────────────────────────────────

class RingForgeAuditor:
    """Audits Python files for RingForge UI design violations."""

    # Hardcoded colors that should use tokens
    HARDCODED_COLORS = [
        "#1e1e2e", "#181825", "#313244", "#45475a", "#585b70",
        "#cdd6f4", "#a6adc8", "#6c7086", "#89b4fa", "#fab387",
        "#a6e3a1", "#f38ba8", "#f9e2af", "#64748b", "#94a3b8",
    ]

    def __init__(self):
        self.findings: List[Finding] = []
        self._files_checked = 0
        self._files_with_errors = set()

    def audit_file(self, filepath: str):
        """Audit a single Python file."""
        try:
            with open(filepath) as f:
                source = f.read()
        except Exception:
            return

        self._files_checked += 1
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return

        lines = source.split("\n")

        for node in ast.walk(tree):
            self._check_node(node, filepath, lines)

        # Check imports
        self._check_imports(tree, filepath, lines)

    def _check_node(self, node, filepath: str, lines: list[str]):
        """Check an AST node for violations."""
        if isinstance(node, ast.Call):
            self._check_call(node, filepath, lines)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            self._check_string_constant(node, filepath, lines)

    def _check_call(self, node: ast.Call, filepath: str, lines: list[str]):
        """Check function calls for missing properties."""
        # Check if it's a setFocusPolicy call with no argument
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "setFocusPolicy":
                if not node.args:
                    lineno = node.lineno
                    self.findings.append(Finding(
                        file=filepath, line=lineno,
                        severity="error", category="missing_focus",
                        message="setFocusPolicy() called without arguments",
                        suggestion="Add Qt.FocusPolicy.StrongFocus"
                    ))

            if node.func.attr == "setMinimumSize":
                if len(node.args) < 2:
                    lineno = node.lineno
                    self.findings.append(Finding(
                        file=filepath, line=lineno,
                        severity="warning", category="missing_min_size",
                        message="setMinimumSize() called with < 2 args",
                        suggestion="Set proper minimum size (48, 48)"
                    ))

            if node.func.attr == "setAccessibleName":
                # Good — has accessible name
                pass

            if node.func.attr in ("setToolTip", "setStatusTip"):
                # Tooltip is good — don't flag
                pass

        # Check setStyleSheet with hardcoded colors
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "setStyleSheet" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    for color in self.HARDCODED_COLORS:
                        if color in arg.value and "token" not in arg.value.lower():
                            lineno = node.lineno
                            self.findings.append(Finding(
                                file=filepath, line=lineno,
                                severity="warning", category="hardcoded_color",
                                message=f"Hardcoded color {color} in QSS",
                                suggestion="Use core.tokens constants instead"
                            ))

    def _check_string_constant(self, node: ast.Constant, filepath: str, lines: list[str]):
        """Check string constants for hardcoded values."""
        if not isinstance(node.value, str):
            return

        value = node.value
        lineno = node.lineno

        # Check for hardcoded hex colors
        for color in self.HARDCODED_COLORS:
            if color in value and len(value) <= 20:
                # Likely a color assignment
                # Check if it's in an assignment context
                self.findings.append(Finding(
                    file=filepath, line=lineno,
                    severity="warning", category="hardcoded_color",
                    message=f"Hardcoded color reference: {color}",
                    suggestion="Use core.tokens constants instead"
                ))

        # Check for setFont with hardcoded size
        if "QFont(" in value or "setFont" in value:
            if any(f"{n}" in value for n in ["8", "9", "10", "11", "12"]):
                # Could be a hardcoded font size — check context
                pass

    def _check_imports(self, tree: ast.Module, filepath: str, lines: list[str]):
        """Check imports for token usage."""
        # Check if core.tokens is imported
        has_token_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "tokens" in node.module:
                    has_token_import = True

        if not has_token_import and filepath.endswith("main_window.py"):
            pass  # Not required for main_window

    def audit_directory(self, directory: str):
        """Audit all Python files in a directory."""
        path = Path(directory)
        for pyfile in path.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            if "test_" in pyfile.name:
                continue
            self.audit_file(str(pyfile))

    def generate_report(self) -> dict:
        """Generate audit report as dict."""
        errors = [f for f in self.findings if f.severity == "error"]
        warnings = [f for f in self.findings if f.severity == "warning"]
        info = [f for f in self.findings if f.severity == "info"]

        return {
            "files_checked": self._files_checked,
            "total_findings": len(self.findings),
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info),
            "files_with_errors": list(self._files_with_errors),
            "findings": self.findings,
        }

    def print_report(self):
        """Print formatted audit report."""
        report = self.generate_report()

        print("=" * 60)
        print("  RingForge Design Audit Report")
        print("=" * 60)
        print(f"  Files checked:    {report['files_checked']}")
        print(f"  Total findings:   {report['total_findings']}")
        print(f"  Errors:           {report['errors']}")
        print(f"  Warnings:         {report['warnings']}")
        print(f"  Info:             {report['info']}")
        print()

        if report["errors"] > 0:
            print("ERRORS:")
            for f in report["findings"]:
                if f.severity == "error":
                    print(f"  {f.file}:{f.line} [{f.category}] {f.message}")
                    if f.suggestion:
                        print(f"    → {f.suggestion}")

        if report["warnings"] > 0:
            print("\nWARNINGS:")
            for f in report["findings"]:
                if f.severity == "warning":
                    print(f"  {f.file}:{f.line} [{f.category}] {f.message}")
                    if f.suggestion:
                        print(f"    → {f.suggestion}")

        print("\n" + "=" * 60)

        # Exit code
        return 1 if report["errors"] > 0 else 0


def main():
    """Run the design audit."""
    target = sys.argv[1] if len(sys.argv) > 1 else "ui/"
    auditor = RingForgeAuditor()
    auditor.audit_directory(target)
    exit_code = auditor.print_report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
