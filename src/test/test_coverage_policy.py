from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_branch_coverage_is_configured_with_a_floor():
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert '"pytest-cov>=7.1.0"' in pyproject
    assert "[tool.coverage.run]" in pyproject
    assert "branch = true" in pyproject
    assert 'source = ["dip_coater", "trinamic_wrapper"]' in pyproject
    assert "[tool.coverage.report]" in pyproject
    assert "show_missing = true" in pyproject
    assert "fail_under = " in pyproject


def test_ci_reports_and_uploads_coverage():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "--cov=dip_coater" in workflow
    assert "--cov=trinamic_wrapper" in workflow
    assert "--cov-branch" in workflow
    assert "--cov-report=term-missing" in workflow
    assert "--cov-report=xml" in workflow
    assert "actions/upload-artifact@v7" in workflow
    assert "path: coverage.xml" in workflow
