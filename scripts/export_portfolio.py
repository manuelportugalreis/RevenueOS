"""Export review copies, scenario sensitivity, source archive and integrity provenance."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from revenueos.comparison import business_scenario


def main() -> None:
    output = Path("outputs")
    output.mkdir(exist_ok=True)
    assumptions = json.loads(Path("data/evaluation/business-assumptions.json").read_text())
    scenarios = []
    for minutes in assumptions["sensitivity_assisted_minutes"]:
        scenarios.append(
            business_scenario({**assumptions["base"], "assisted_minutes_including_review": minutes})
        )
    (output / "RevenueOS-Business-Scenarios.json").write_text(
        json.dumps(
            {
                "evidence_class": "simulation_not_observed",
                "source": assumptions,
                "scenarios": scenarios,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mapping = {
        "README.md": "RevenueOS-GitHub-README.md",
        "docs/19-dashboard-guide.md": "RevenueOS-Dashboard-Guide.md",
        "docs/20-dashboard-verification.md": "RevenueOS-Dashboard-Verification.md",
        "docs/23-comparison-report.md": "RevenueOS-Technical-Report.md",
        "docs/24-business-case.md": "RevenueOS-Business-Case.md",
        "docs/25-case-study.md": "RevenueOS-Case-Study.md",
        "docs/26-interview-demo.md": "RevenueOS-Interview-Demo.md",
        "docs/architecture.svg": "RevenueOS-Architecture.svg",
    }
    for source, target in mapping.items():
        (output / target).write_bytes(Path(source).read_bytes())
    for name in (
        "data/evaluation/business-assumptions.json",
        "data/pilot/task-observations-template.csv",
    ):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(name).read_bytes())
    (output / "RevenueOS-Portfolio-Index.md").write_text(
        "# RevenueOS: evaluation and portfolio evidence\n\n"
        "Synthetic, offline engineering demonstration. No client outcomes or realized ROI.\n\n"
        "174 Python/PostgreSQL tests and two Chromium journeys passed. "
        "Paired authored task success: 85/100 assisted versus 66/100 reference; "
        "recommendation quality gates still failed.\n\n"
        "- [Technical report](RevenueOS-Technical-Report.md)\n"
        "- [Architecture](RevenueOS-Architecture.svg)\n"
        "- [Business case](RevenueOS-Business-Case.md)\n"
        "- [Engineering case study](RevenueOS-Case-Study.md)\n"
        "- [GitHub README](RevenueOS-GitHub-README.md)\n"
        "- [Five-minute interview demo](RevenueOS-Interview-Demo.md)\n"
        "- [Dashboard operations](RevenueOS-Dashboard-Guide.md)\n"
        "- [Verification and remaining risks](RevenueOS-Dashboard-Verification.md)\n"
        "- [Raw attempts](RevenueOS-Comparison-Attempts.jsonl)\n"
        "- [Comparison JSON](RevenueOS-Workflow-Comparison.json)\n"
        "- [Simulated scenarios](RevenueOS-Business-Scenarios.json)\n"
        "- [Source archive](RevenueOS-Portfolio-Source.zip)\n"
        "- [Content provenance](RevenueOS-Portfolio-Provenance.json)\n\n"
        "![Synthetic dashboard](RevenueOS-Dashboard-Desktop.png)\n",
        encoding="utf-8",
    )
    # Preserve README-relative documentation links in exported review copies.
    for source in Path("docs").glob("*"):
        if source.is_file():
            target = output / "docs" / source.name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(source.read_bytes())
    files = [
        Path(name)
        for name in (
            "README.md",
            ".env.example",
            ".gitignore",
            ".dockerignore",
            "Dockerfile",
            "alembic.ini",
            "compose.yaml",
            "pyproject.toml",
            "requirements.lock",
        )
    ]
    for folder in (
        "src",
        "migrations",
        "tests",
        "scripts",
        "docs",
        "data",
        ".github",
        "frontend",
        "deploy",
    ):
        files.extend(
            path
            for path in Path(folder).rglob("*")
            if path.is_file()
            and not {
                "node_modules",
                "dist",
                "test-results",
                "playwright-report",
                "__pycache__",
            }.intersection(path.parts)
            and not any(part.endswith(".egg-info") for part in path.parts)
            and path.suffix not in (".pyc", ".pyo")
        )
    archive = output / "RevenueOS-Portfolio-Source.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(files):
            bundle.write(path, path.as_posix())
    with ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert "frontend/package-lock.json" in bundle.namelist()
        assert "src/revenueos/comparison.py" in bundle.namelist()
    comparison = json.loads((output / "RevenueOS-Workflow-Comparison.json").read_text())
    raw = output / "RevenueOS-Comparison-Attempts.jsonl"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == comparison["raw_sha256"]
    assert sum(1 for _ in raw.open()) == comparison["raw_attempts"] == 408
    artifacts = [path for path in output.glob("RevenueOS-*") if path.is_file()]
    manifest = {
        "source_archive": archive.name,
        "source_file_count": len(files),
        "source_hashes": {
            path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)
        },
        "artifact_hashes": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifacts)
            if path.name
            not in ("RevenueOS-Portfolio-Provenance.json", "RevenueOS-Portfolio-Package.zip")
        },
        "comparison_raw_hash_valid": True,
        "client_outcomes": "not_measured",
        "note": (
            "Uncommitted workspace snapshot; hashes identify contents, not a released Git commit."
        ),
    }
    (output / "RevenueOS-Portfolio-Provenance.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    names = [
        *mapping.values(),
        "RevenueOS-Portfolio-Index.md",
        "RevenueOS-Portfolio-Source.zip",
        "RevenueOS-Portfolio-Provenance.json",
        "RevenueOS-Workflow-Comparison.json",
        "RevenueOS-Comparison-Attempts.jsonl",
        "RevenueOS-Business-Scenarios.json",
        "portfolio-tests.xml",
        "dashboard-browser-tests.xml",
        "RevenueOS-Dashboard-Desktop.png",
        "RevenueOS-Dashboard-Mobile.png",
        "RevenueOS-Dashboard-Approval.png",
    ]
    package = output / "RevenueOS-Portfolio-Package.zip"
    with ZipFile(package, "w", ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.write(output / name, name)
        for path in (output / "docs").glob("*"):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
        for path in (output / "data").rglob("*"):
            if path.is_file():
                bundle.write(path, path.relative_to(output).as_posix())
    with ZipFile(package) as bundle:
        assert bundle.testzip() is None
    print(
        f"Exported portfolio documentation, three simulated scenarios "
        f"and {len(files)} source files."
    )


if __name__ == "__main__":
    main()
