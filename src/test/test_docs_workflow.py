from pathlib import Path


def test_mkdocs_github_pages_workflow_is_configured():
    workflow_path = Path(__file__).parents[2] / ".github" / "workflows" / "docs.yml"

    workflow = workflow_path.read_text()

    assert "name: Deploy MkDocs" in workflow
    assert "branches: [main]" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "uv sync --extra docs --locked" in workflow
    assert "uv run mkdocs build --strict" in workflow
    assert "actions/upload-pages-artifact@" in workflow
    assert "actions/deploy-pages@" in workflow
