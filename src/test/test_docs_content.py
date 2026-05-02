from pathlib import Path


def test_install_docs_explain_software_updates_and_version_check():
    install_docs = (Path(__file__).parents[2] / "docs" / "install.md").read_text()

    assert "python3 -m pip install dip-coater" in install_docs
    assert "python3 -m pip install --upgrade dip-coater" in install_docs
    assert "dip-coater --version" in install_docs
    assert "uv run dip-coater --version" in install_docs
    assert "## Source Checkout Install" in install_docs
    assert "## Update the Software" in install_docs
    assert "If you installed from a source checkout" in install_docs
    assert "git pull" in install_docs
    assert "python3 -m pip install --upgrade -e ." in install_docs
    assert "uv sync" in install_docs
    assert "version shown at the top of the UI" in install_docs


def test_developer_setup_docs_match_large_profile_defaults():
    developer_docs = (
        Path(__file__).parents[2] / "docs" / "developer-setups.md"
    ).read_text()

    assert "DEFAULT_REFERENCE_LEFT_STOP_ENABLED = True" in developer_docs
    assert "DEFAULT_REFERENCE_RIGHT_STOP_ENABLED = True" in developer_docs
    assert "Defaults to `HomeDirection.DOWN`" in developer_docs


def test_coder_docs_explain_trusted_scripts_and_stop_button():
    coder_docs = (Path(__file__).parents[2] / "docs" / "coder-api.md").read_text()

    assert "trusted Python code" in coder_docs
    assert "STOP code" in coder_docs
    assert "between Coder API calls" in coder_docs


def test_run_docs_explain_session_log_file():
    run_docs = (Path(__file__).parents[2] / "docs" / "run-the-app.md").read_text()

    assert "--session-log-file" in run_docs
    assert "DIP_COATER_SESSION_LOG_FILE" in run_docs
    assert "JSON lines" in run_docs


def test_python_examples_docs_reference_example_scripts():
    examples_docs = (
        Path(__file__).parents[2] / "docs" / "python-examples.md"
    ).read_text()

    assert "examples/tmc2209_example.py" in examples_docs
    assert "examples/tmc2660_example.py" in examples_docs
    assert "examples/tmc5160_example.py" in examples_docs
    assert "examples/tmc5160_homing_example.py" in examples_docs
    assert "--real-hardware" in examples_docs
