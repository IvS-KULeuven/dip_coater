from pathlib import Path


def test_install_docs_explain_software_updates_and_version_check():
    install_docs = (Path(__file__).parents[2] / "docs" / "install.md").read_text()

    assert "## Update the Software" in install_docs
    assert "git pull" in install_docs
    assert "python3 -m pip install --upgrade -e ." in install_docs
    assert "uv sync" in install_docs
    assert "version shown at the top of the UI" in install_docs
