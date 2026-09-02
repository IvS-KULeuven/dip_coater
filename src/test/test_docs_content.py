from pathlib import Path


def test_install_docs_explain_software_updates_and_version_check():
    install_docs = (Path(__file__).parents[2] / "docs" / "install.md").read_text()

    assert "python3 -m pip install dip-coater" in install_docs
    assert 'python3 -m pip install "dip-coater[syntax]"' in install_docs
    assert "python3 -m pip install --upgrade dip-coater" in install_docs
    assert ".\\.venv\\Scripts\\Activate.ps1" in install_docs
    assert ".venv\\Scripts\\activate.bat" in install_docs
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
    assert "between Python lines" in coder_docs
    assert "native-library call" in coder_docs


def test_coder_examples_use_explicit_keyword_arguments():
    root = Path(__file__).parents[2]
    docs_coder = (root / "docs" / "coder-api.md").read_text()
    bundled_coder = (root / "src" / "dip_coater" / "coder_API.md").read_text()
    help_docs = (root / "src" / "dip_coater" / "help.md").read_text()
    initial_code = (
        root / "src" / "dip_coater" / "code_editor_init_content.py"
    ).read_text()

    assert "self.move_down(distance_mm=10, speed_mm_s=5)" in docs_coder
    assert (
        "self.move_down(distance_mm=10, speed_mm_s=5, acceleration_mm_s2=10)"
        in docs_coder
    )
    assert "self.move_up(distance_mm=10, speed_mm_s=5)" in bundled_coder
    assert "self.move_to_position(position_mm=10, speed_mm_s=5)" in bundled_coder
    assert "self.move_down(distance_mm=10, speed_mm_s=5)" in help_docs
    assert (
        "self.move_down(distance_mm=distance_down, speed_mm_s=speed_down)"
        in initial_code
    )
    assert "self.move_down(10, 5)" not in docs_coder
    assert "self.move_up(10, 2)" not in help_docs


def test_run_docs_explain_session_log_file():
    run_docs = (Path(__file__).parents[2] / "docs" / "run-the-app.md").read_text()

    assert "--session-log-file" in run_docs
    assert "DIP_COATER_SESSION_LOG_FILE" in run_docs
    assert "JSON lines" in run_docs


def test_troubleshooting_docs_include_windows_venv_activation():
    troubleshooting_docs = (
        Path(__file__).parents[2] / "docs" / "troubleshooting.md"
    ).read_text()

    assert "source .venv/bin/activate" in troubleshooting_docs
    assert ".\\.venv\\Scripts\\Activate.ps1" in troubleshooting_docs
    assert ".venv\\Scripts\\activate.bat" in troubleshooting_docs


def test_python_examples_docs_reference_example_scripts():
    examples_docs = (
        Path(__file__).parents[2] / "docs" / "python-examples.md"
    ).read_text()

    assert "examples/tmc2209_example.py" in examples_docs
    assert "examples/tmc2660_example.py" in examples_docs
    assert "examples/tmc5160_example.py" in examples_docs
    assert "examples/tmc5160_homing_example.py" in examples_docs
    assert "--real-hardware" in examples_docs


def test_hardware_docs_do_not_claim_tmc2660_supports_large_reference_switches():
    root = Path(__file__).parents[2]
    run_docs = (root / "docs" / "run-the-app.md").read_text()
    hardware_docs = (root / "docs" / "hardware-setup.md").read_text()
    examples_docs = (root / "docs" / "python-examples.md").read_text()

    for content in (run_docs, hardware_docs, examples_docs):
        assert "TMC2660 cannot read the `large` profile's driver-reference" in content

    assert (
        "tmc2660_example.py --real-hardware --port interactive" not in examples_docs
    )


def test_tmc2660_parameter_docs_distinguish_set_and_read_microstep_values():
    parameter_docs = (
        Path(__file__).parents[2] / "docs" / "TMC2660_EVALParameters.md"
    ).read_text()

    assert "Set AP 140 with the physical microstep count" in parameter_docs
    assert "readback is the base-2 exponent" in parameter_docs


def test_python_api_docs_are_configured_for_docstring_reference():
    root = Path(__file__).parents[2]
    pyproject = (root / "pyproject.toml").read_text()
    mkdocs = (root / "mkdocs.yml").read_text()
    api_index = (root / "docs" / "api" / "index.md").read_text()
    motion_docs = (root / "docs" / "api" / "motion-controller.md").read_text()
    setup_docs = (root / "docs" / "api" / "setup-profiles.md").read_text()

    assert "mkdocstrings[python]" in pyproject
    assert "mkdocstrings" in mkdocs
    assert "docstring_style: sphinx" in mkdocs
    assert "Overview: api/index.md" in mkdocs
    assert "Motion Controller: api/motion-controller.md" in mkdocs
    assert "Motor Drivers: api/motor-drivers.md" in mkdocs
    assert "::: dip_coater.services.motion_controller.MotionController" in motion_docs
    assert "::: dip_coater.setup_profiles.machine_profile.MachineProfile" in setup_docs
    assert "motion-controller.md" in api_index


def test_mkdocs_navigation_groups_user_and_developer_pages():
    mkdocs = (Path(__file__).parents[2] / "mkdocs.yml").read_text()

    assert "  - Dip Coater:\n      - Start: index.md" in mkdocs
    assert "      - Troubleshooting: troubleshooting.md" in mkdocs
    assert "\n  - Troubleshooting: troubleshooting.md" not in mkdocs
    assert (
        "  - Developer:\n"
        "      - Notes: developer-notes.md\n"
        "      - Setup Profiles: developer-setups.md"
    ) in mkdocs
    assert "\n  - Developer Notes: developer-notes.md" not in mkdocs
    assert "\n  - Developer Setup Profiles: developer-setups.md" not in mkdocs
