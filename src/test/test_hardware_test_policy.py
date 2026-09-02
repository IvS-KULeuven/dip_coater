from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_hardware_suites_require_explicit_enablement_and_motion_opt_in():
    pyproject = (ROOT / "pyproject.toml").read_text()
    wrapper_tests = (
        ROOT / "src" / "trinamic_wrapper" / "tests" / "hardware" / "test_hardware.py"
    ).read_text()
    wrapper_fixtures = (
        ROOT / "src" / "trinamic_wrapper" / "tests" / "hardware" / "conftest.py"
    ).read_text()
    tmc5160_tests = (ROOT / "src" / "test" / "test_tmc5160_hardware.py").read_text()
    tmc2209_tests = (ROOT / "src" / "test" / "test_tmc2209_hardware.py").read_text()

    assert "hardware_motion: supervised hardware tests that physically move a motor" in pyproject
    assert "pytestmark = pytest.mark.hardware" in wrapper_tests
    assert "@pytest.mark.hardware_motion\nclass TestMotion" in wrapper_tests
    assert 'group.addoption(\n        "--run-hardware",' in wrapper_fixtures
    assert 'group.addoption(\n        "--run-hardware-motion",' in wrapper_fixtures
    assert "@pytest.mark.hardware_motion\ndef test_tmc5160_hardware_optional_motion" in tmc5160_tests
    assert 'DIP_COATER_TMC5160_HARDWARE' in tmc5160_tests
    assert "pytestmark = pytest.mark.hardware" in tmc2209_tests
    assert "@pytest.mark.hardware_motion\ndef test_tmc2209_hardware_optional_motion" in tmc2209_tests
    assert 'DIP_COATER_TMC2209_HARDWARE' in tmc2209_tests


def test_hardware_workflow_is_manual_supervised_and_current_limited():
    workflow = (ROOT / ".github" / "workflows" / "hardware-tests.yml").read_text()

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "\n  pull_request:" not in workflow
    assert "type: choice" in workflow
    assert "type: boolean" in workflow
    assert "default: false" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "environment: dip-coater-hardware-motion" in workflow
    assert 'hardware and not hardware_motion' in workflow
    assert '-m "hardware_motion"' in workflow
    assert "--hw-current-mA 500" in workflow
    assert "--hw-max-mA 1000" in workflow
    assert "DIP_COATER_TMC5160_CURRENT_MA: \"500\"" in workflow
    assert "DIP_COATER_TMC2209_CURRENT_MA: \"500\"" in workflow
    for runner_label in ("tmc5160", "tmc2660", "tmc2209"):
        assert runner_label in workflow


def test_developer_docs_explain_hardware_test_safety_gates():
    developer_docs = (ROOT / "docs" / "developer-notes.md").read_text()
    non_motion_command, motion_section = developer_docs.split(
        "Optional motion smoke test:", maxsplit=1
    )

    assert "Hardware-in-the-loop tests" in developer_docs
    assert "DIP_COATER_TMC5160_HARDWARE=1" in non_motion_command
    assert 'pytest -m "hardware and not hardware_motion"' in non_motion_command
    assert "DIP_COATER_TMC5160_RUN_MOTION=1" in motion_section
    assert "pytest -m hardware_motion" in motion_section
    assert "--run-hardware" in developer_docs
    assert "--run-hardware-motion" in developer_docs
    assert "dip-coater-hardware-motion" in developer_docs
