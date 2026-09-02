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


def test_app_ci_workflow_runs_tests_lint_and_docs():
    workflow_path = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"

    workflow = workflow_path.read_text()

    assert "name: CI" in workflow
    assert 'python-version: "3.10"' in workflow
    assert "uv run pytest -q -m \"not hardware\"" in workflow
    assert "uv run ruff check src" in workflow
    assert "uv run --extra docs mkdocs build --strict" in workflow


def test_developer_docs_reference_the_active_pages_workflow():
    root = Path(__file__).parents[2]
    developer_docs = (root / "docs" / "developer-notes.md").read_text()

    assert ".github/workflows/docs.yml" in developer_docs
    assert "mkdocs gh-deploy --force" not in developer_docs
