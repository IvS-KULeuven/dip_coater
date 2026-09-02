from pathlib import Path


ROOT = Path(__file__).parents[2]

TYPED_BOUNDARIES = (
    "src/dip_coater/mechanical/mechanical_setup.py",
    "src/dip_coater/setup_profiles/machine_profile.py",
    "src/dip_coater/setup_profiles/registry.py",
    "src/dip_coater/motor_driver/motor_driver_interface.py",
    "src/dip_coater/services/motion_controller.py",
)


def test_gradual_mypy_scope_is_configured():
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert '"mypy>=2.3.1"' in pyproject
    assert "[tool.mypy]" in pyproject
    assert 'python_version = "3.10"' in pyproject
    assert "check_untyped_defs = true" in pyproject
    assert "no_implicit_optional = true" in pyproject
    assert "warn_return_any = true" in pyproject
    assert "warn_unused_configs = true" in pyproject
    for boundary in TYPED_BOUNDARIES:
        assert f'    "{boundary}",' in pyproject


def test_ci_runs_gradual_type_check():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "uv run mypy" in workflow


def test_developer_docs_explain_how_to_expand_the_typed_scope():
    developer_docs = (ROOT / "docs" / "developer-notes.md").read_text()

    assert "uv run mypy" in developer_docs
    assert "Gradual typing" in developer_docs
    assert "files" in developer_docs
