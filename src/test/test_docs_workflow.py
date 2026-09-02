from pathlib import Path


def test_mkdocs_github_pages_workflow_is_configured():
    workflow_path = Path(__file__).parents[2] / ".github" / "workflows" / "docs.yml"

    workflow = workflow_path.read_text()

    assert "name: Deploy MkDocs" in workflow
    assert "branches: [develop]" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "uv sync --extra docs --locked" in workflow
    assert "uv run mkdocs build --strict" in workflow
    assert "actions/upload-pages-artifact@" in workflow
    assert "actions/deploy-pages@" in workflow
    assert '      - "src/dip_coater/**"' in workflow


def test_ci_matrix_covers_supported_python_and_windows():
    workflow_path = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"

    workflow = workflow_path.read_text()

    assert "name: CI" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "runs-on: ${{ matrix.os }}" in workflow
    assert "matrix:" in workflow
    assert "os: ubuntu-latest" in workflow
    assert "os: windows-latest" in workflow
    assert 'python-version: "3.10"' in workflow
    assert 'python-version: "3.14"' in workflow
    assert "uv run pytest -q -m \"not hardware\"" in workflow


def test_ci_runs_quality_docs_build_and_clean_wheel_smoke_test():
    workflow = (
        Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"
    ).read_text()

    assert "uv run ruff check ." in workflow
    assert "uv run --extra docs mkdocs build --strict" in workflow
    assert "uv build --no-sources" in workflow
    assert "--no-project" in workflow
    assert "dip-coater --version" in workflow


def test_ci_has_no_duplicate_unit_test_workflow():
    duplicate = Path(__file__).parents[2] / ".github" / "workflows" / "unit-tests.yml"

    assert not duplicate.exists()


def test_workflows_use_maintained_action_majors():
    workflows = Path(__file__).parents[2] / ".github" / "workflows"
    contents = "\n".join(path.read_text() for path in workflows.glob("*.yml"))

    assert "actions/checkout@v4" not in contents
    assert "actions/setup-python@v5" not in contents
    assert "astral-sh/setup-uv@v5" not in contents
    assert "actions/checkout@v6" in contents
    assert "actions/setup-python@v6" in contents
    assert "astral-sh/setup-uv@v9" in contents

    docs_workflow = (workflows / "docs.yml").read_text()
    assert "actions/upload-pages-artifact@v5" in docs_workflow
    assert "actions/deploy-pages@v5" in docs_workflow


def test_developer_docs_reference_the_active_pages_workflow():
    root = Path(__file__).parents[2]
    developer_docs = (root / "docs" / "developer-notes.md").read_text()

    assert ".github/workflows/docs.yml" in developer_docs
    assert "mkdocs gh-deploy --force" not in developer_docs
