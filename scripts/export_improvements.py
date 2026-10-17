"""Export the current synthetic improvement evidence without overwriting v1 artifacts."""

import csv
import hashlib
import json
import random
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    output = Path("outputs/improvements")
    final = output / "final-ablation"
    report = json.loads((final / "RevenueOS-Workflow-Comparison.json").read_text(encoding="utf-8"))
    raw = final / "RevenueOS-Comparison-Attempts.jsonl"
    assert digest(raw) == report["raw_sha256"]
    assert len(raw.read_text(encoding="utf-8").splitlines()) == report["raw_attempts"] == 816
    assert all(digest(Path(name)) == value for name, value in report["source_hashes"].items())
    assert all(
        digest(Path("data/intelligence") / name) == value
        for name, value in report["fixture_hashes"].items()
    )

    # Independent ratings remain blank; expected labels and arm names are separate.
    cases = {
        c["id"]: c
        for c in json.loads(Path("data/intelligence/cases.json").read_text(encoding="utf-8"))[
            "cases"
        ]
    }
    attempts = [
        json.loads(line)
        for line in raw.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["phase"] == "measured" and json.loads(line)["repetition"] == 0
    ]
    random.Random(20261016).shuffle(attempts)
    with (
        (output / "RevenueOS-Independent-Review-Blank.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f,
        (output / "RevenueOS-Review-Coordinator-Key.csv").open(
            "w", newline="", encoding="utf-8"
        ) as k,
    ):
        writer = csv.writer(f)
        key = csv.writer(k)
        writer.writerow(
            [
                "review_id",
                "synthetic_query",
                "observed_state",
                "output_json",
                "relevance_0_2",
                "grounding_0_2",
                "abstention_appropriate",
                "comments",
            ]
        )
        key.writerow(
            ["review_id", "case_id", "arm", "fixture_expect_abstention", "fixture_success"]
        )
        for index, row in enumerate(attempts, 1):
            identifier = f"R{index:04}"
            writer.writerow(
                [
                    identifier,
                    cases[row["case_id"]]["query"],
                    row["state"],
                    json.dumps(row["output"]),
                    "",
                    "",
                    "",
                    "",
                ]
            )
            key.writerow(
                [
                    identifier,
                    row["case_id"],
                    row["arm"],
                    row["expect_abstention"],
                    row["fixture_success"],
                ]
            )

    for folder in ("docs", "data"):
        for path in Path(folder).rglob("*"):
            if path.is_file():
                target = output / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    (output / "README.md").write_text(
        Path("README.md").read_text(encoding="utf-8").replace("outputs/improvements/", ""),
        encoding="utf-8",
    )
    for source, target in (
        ("docs/29-improvements-verification.md", "RevenueOS-Improvements-Report.md"),
        ("docs/28-improvements-guide.md", "RevenueOS-Improvements-Guide.md"),
    ):
        contents = re.sub(
            r"\]\((\d[^)]+\.md)\)", r"](docs/\1)", Path(source).read_text(encoding="utf-8")
        )
        (output / target).write_text(contents, encoding="utf-8")
    (output / "RevenueOS-Review-Instructions.md").write_text(
        "# Independent review packet: not yet reviewed\n\n"
        "400 shuffled synthetic outputs from the first repetition of four arms. "
        "All ratings are blank. No independent review has occurred.\n\n"
        "A coordinator should share only the blank CSV, queries and approved corpus "
        "(`data/intelligence/corpus.json`), not the coordinator key or automated scores. "
        "Ask two independent reviewers to rate relevance and grounding (0 unacceptable, "
        "1 requires correction, 2 acceptable), whether abstention is appropriate, and reasons. "
        "Preserve disagreements and adjudicate before opening the key. This packet "
        "is preparation, not blinded human evidence or a new held-out dataset.\n",
        encoding="utf-8",
    )
    (output / "RevenueOS-Improvements-Index.md").write_text(
        "# RevenueOS: five improvements\n\n"
        "Everything remains fictitious. No company, real participant, "
        "live-model evaluation or realized ROI.\n\n"
        "- [Executed report and remaining risks](RevenueOS-Improvements-Report.md)\n"
        "- [Design, alternatives and walkthrough](RevenueOS-Improvements-Guide.md)\n"
        "- [Current GitHub README](README.md)\n"
        "- [Architecture](docs/22-architecture-current.md)\n"
        "- [Final four-arm comparison](final-ablation/RevenueOS-Workflow-Comparison.json)\n"
        "- [Final raw attempts](final-ablation/RevenueOS-Comparison-Attempts.jsonl)\n"
        "- [Local performance observations](RevenueOS-Performance.json)\n"
        "- [Restore integrity](RevenueOS-Restore-Drill.json) and "
        "[post-restore permissions](RevenueOS-Restore-Security-Check.json)\n"
        "- [Scripted business rehearsal](RevenueOS-Fictitious-Rehearsal.json)\n"
        "- [Independent review preparation](RevenueOS-Review-Instructions.md)\n"
        "- [Python tests](python-tests.xml), [ACL regression](runtime-acl-tests.xml), "
        "[browser journeys](dashboard-browser-tests.xml)\n"
        "- [Source archive](RevenueOS-Improvements-Source.zip) and "
        "[integrity manifest](RevenueOS-Improvements-Provenance.json)\n\n"
        "The root comparison in this folder is an earlier v2 execution; "
        "`final-ablation/` is the final source-matched run. "
        "The final repeat followed an operational ACL fix only, without evidence-policy tuning. "
        "Older v1 artifacts outside this folder remain historical.\n\n"
        "![Synthetic executive dashboard](RevenueOS-Dashboard-Desktop.png)\n",
        encoding="utf-8",
    )

    roots = [
        "src",
        "migrations",
        "tests",
        "scripts",
        "docs",
        "data",
        ".github",
        "deploy",
        "frontend",
    ]
    files = [
        p
        for name in roots
        for p in Path(name).rglob("*")
        if p.is_file()
        and not any(
            x in p.parts
            for x in ("node_modules", "dist", "__pycache__", "test-results", "playwright-report")
        )
        and p.suffix not in (".pyc", ".pyo")
    ]
    files += [
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
    source = output / "RevenueOS-Improvements-Source.zip"
    with ZipFile(source, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.as_posix())
    with ZipFile(source) as archive:
        assert archive.testzip() is None
        assert "src/revenueos/evidence.py" in archive.namelist()
        assert not any(
            "node_modules/" in name or name.endswith("/.env") for name in archive.namelist()
        )
    manifest_path = output / "RevenueOS-Improvements-Provenance.json"
    package_path = output / "RevenueOS-Improvements-Package.zip"
    artifacts = [
        p for p in output.rglob("*") if p.is_file() and p not in (manifest_path, package_path)
    ]
    manifest_path.write_text(
        json.dumps(
            {
                "source_files": len(files),
                "source_hashes": {p.as_posix(): digest(p) for p in sorted(files)},
                "artifact_hashes": {
                    p.relative_to(output).as_posix(): digest(p) for p in sorted(artifacts)
                },
                "final_comparison_source_and_raw_hashes_valid": True,
                "independent_review_status": "not_conducted_blank_packet_only",
                "actual_pilot": "not_run_no_company",
                "note": "Uncommitted workspace snapshot; content hashes are not a release commit.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with ZipFile(package_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted([*artifacts, manifest_path]):
            archive.write(path, path.relative_to(output).as_posix())
    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
    print(
        f"Exported {len(files)} source files, 400 blank review rows and verified evidence hashes."
    )


if __name__ == "__main__":
    main()
