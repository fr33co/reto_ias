"""Documentation gate: every module, class, function and method of the application must have a docstring."""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"


def _undocumented(path: Path) -> list[str]:
    """List the undocumented definitions (and module) of one source file as `file:line name`."""
    tree = ast.parse(path.read_text())
    missing: list[str] = []
    if not ast.get_docstring(tree) and tree.body:
        missing.append(f"{path.name}: module")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
            missing.append(f"{path.name}:{node.lineno} {node.name}")
    return missing


def test_every_definition_in_the_application_has_a_docstring():
    """Fail with the full list of undocumented modules, classes, functions and methods."""
    missing = [m for p in sorted(APP.rglob("*.py")) if p.name != "__init__.py" for m in _undocumented(p)]
    assert not missing, "Missing docstrings:\n" + "\n".join(missing)
