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


def test_app_ci_workflow_runs_tests_lint_and_docs():
    workflow_path = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"

    workflow = workflow_path.read_text()

    assert "name: CI" in workflow
    assert 'python-version: "3.10"' in workflow
    assert "uv run pytest -q -m \"not hardware\"" in workflow
    assert "uv run ruff check src" in workflow
    assert "uv run --extra docs mkdocs build --strict" in workflow


def test_unit_tests_github_workflow_runs_non_hardware_tests():
    workflow_path = (
        Path(__file__).parents[2] / ".github" / "workflows" / "unit-tests.yml"
    )

    workflow = workflow_path.read_text()

    assert "name: Unit Tests" in workflow
    assert "pull_request:" in workflow
    assert "branches: [develop]" in workflow
    assert 'python-version: "3.10"' in workflow
    assert "uv sync --locked" in workflow
    assert "uv run pytest -q -m \"not hardware\"" in workflow
