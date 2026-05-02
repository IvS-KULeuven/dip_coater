import ast
import py_compile
from pathlib import Path


ROOT = Path(__file__).parents[2]
EXAMPLES = ROOT / "examples"


def test_easy_driver_example_filenames_exist():
    assert (EXAMPLES / "tmc2209_example.py").is_file()
    assert (EXAMPLES / "tmc2660_example.py").is_file()
    assert (EXAMPLES / "tmc5160_example.py").is_file()
    assert (EXAMPLES / "tmc5160_homing_example.py").is_file()


def test_driver_examples_use_requested_setup_profiles_and_motion():
    expectations = {
        "tmc2209_example.py": ("AvailableMotorDrivers.TMC2209", "SMALL_COATER"),
        "tmc2660_example.py": ("AvailableMotorDrivers.TMC2660", "LARGE_COATER"),
        "tmc5160_example.py": ("AvailableMotorDrivers.TMC5160", "LARGE_COATER"),
    }

    for filename, (driver, setup) in expectations.items():
        source = (EXAMPLES / filename).read_text(encoding="utf-8")
        assert driver in source
        assert f"AvailableMachineSetups.{setup}" in source
        assert "move_down(" in source
        assert "move_up(" in source
        assert "--real-hardware" in source


def test_tmc5160_homing_example_homes_and_moves_to_positions():
    source = (EXAMPLES / "tmc5160_homing_example.py").read_text(encoding="utf-8")

    assert "AvailableMotorDrivers.TMC5160" in source
    assert "AvailableMachineSetups.LARGE_COATER" in source
    assert "home_async(" in source
    assert "move_to_position(" in source
    assert "POSITION_MOVES" in source
    assert "speed_mm_s" in source


def test_python_example_functions_have_docstrings():
    for script in EXAMPLES.glob("*.py"):
        module = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        functions = [
            node
            for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        assert functions
        assert [node.name for node in functions if ast.get_docstring(node) is None] == []


def test_python_examples_compile():
    for script in EXAMPLES.glob("*.py"):
        py_compile.compile(str(script), doraise=True)
