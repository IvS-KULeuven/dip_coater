import ast
from pathlib import Path


ROOT = Path(__file__).parents[2]

PUBLIC_API_FILES = [
    ROOT / "src/dip_coater/__init__.py",
    ROOT / "src/dip_coater/app_state.py",
    ROOT / "src/dip_coater/config/config_loader.py",
    ROOT / "src/dip_coater/logging/session_log.py",
    ROOT / "src/dip_coater/mechanical/mechanical_setup.py",
    ROOT / "src/dip_coater/motor_driver/driver_registry.py",
    ROOT / "src/dip_coater/motor_driver/motor_driver_interface.py",
    ROOT / "src/dip_coater/services/motion_controller.py",
    ROOT / "src/dip_coater/setup_profiles/machine_profile.py",
    ROOT / "src/dip_coater/setup_profiles/registry.py",
    ROOT / "src/dip_coater/utils/helpers.py",
]


def test_public_api_docstrings_document_parameters_and_returns():
    missing: list[str] = []

    for path in PUBLIC_API_FILES:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for owner, node in _iter_public_api_nodes(module):
            docstring = ast.get_docstring(node) or ""
            location = f"{path.relative_to(ROOT)}:{node.lineno} {owner}{node.name}"

            if not docstring:
                missing.append(f"{location} is missing a docstring")
                continue

            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for parameter in _documented_parameters(node):
                    if f":param {parameter}:" not in docstring:
                        missing.append(
                            f"{location} is missing :param {parameter}:"
                        )
                if _returns_value(node) and ":return:" not in docstring:
                    missing.append(f"{location} is missing :return:")

    assert missing == []


def _iter_public_api_nodes(module: ast.Module):
    for node in module.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            yield "", node
            for child in node.body:
                if _is_public_method(child):
                    yield f"{node.name}.", child
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                yield "", node


def _is_public_method(node: ast.AST) -> bool:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    return node.name == "__init__" or not node.name.startswith("_")


def _documented_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    parameters = [
        argument.arg
        for argument in [*node.args.args, *node.args.kwonlyargs]
        if argument.arg not in {"self", "cls"}
    ]
    if node.args.vararg is not None and node.args.vararg.arg not in {"args"}:
        parameters.append(node.args.vararg.arg)
    if node.args.kwarg is not None and node.args.kwarg.arg not in {"kwargs"}:
        parameters.append(node.args.kwarg.arg)
    return parameters


def _returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.returns is not None:
        return not (
            isinstance(node.returns, ast.Constant) and node.returns.value is None
        )
    return any(
        isinstance(child, ast.Return) and child.value is not None
        for child in ast.walk(node)
    )
