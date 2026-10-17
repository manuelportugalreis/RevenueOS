"""Controlled local synthetic checks; outputs are observations, never production SLOs."""

import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID

import httpx2
from sqlalchemy import event, text

from revenueos.comparison import percentile
from revenueos.db import get_engine
from revenueos.scoring import lead_context, rank_leads, score_context


def main() -> None:
    engine = get_engine()
    org = UUID("11111111-1111-4111-8111-111111111111")
    dataset = UUID(Path("work/intelligence-demo-dataset.txt").read_text().strip())
    with engine.connect() as connection:
        if (
            connection.scalar(text("SELECT data_mode FROM datasets WHERE id=:id"), {"id": dataset})
            != "synthetic"
        ):
            raise ValueError("synthetic_only")
        ids = list(
            connection.scalars(
                text(
                    "SELECT id FROM leads WHERE organization_id=:org AND dataset_id=:id ORDER BY id"
                ),
                {"org": org, "id": dataset},
            )
        )
        # Warm the batched path once; reference uses the unchanged single-lead scoring primitive.
        rank_leads(connection, org, dataset)
    results = {}
    for mode in ("single_lead_reference", "batched_queue"):
        durations, counts = [], []
        for _ in range(3):
            count = []

            def capture(*args: object, count: list[int] = count, **kwargs: object) -> None:
                count.append(1)

            with engine.connect() as connection:
                event.listen(connection, "before_cursor_execute", capture)
                started = time.perf_counter()
                if mode == "single_lead_reference":
                    scores = [
                        score_context(lead_context(connection, org, dataset, lead)) for lead in ids
                    ]
                    fingerprint = {r["lead_id"]: r for r in scores}
                else:
                    scores = rank_leads(connection, org, dataset)["scores"]
                    assert {r["lead_id"]: r for r in scores} == fingerprint
                durations.append((time.perf_counter() - started) * 1000)
                event.remove(connection, "before_cursor_execute", capture)
            counts.append(len(count))
        results[mode] = {
            "latencies_ms": durations,
            "query_counts_including_scope": counts,
            "median_ms": statistics.median(durations),
        }
    engine.dispose()
    base = "http://127.0.0.1:8000"
    headers = {"Origin": base}
    with httpx2.Client(base_url=base, timeout=30) as client:
        response = client.post(
            "/api/auth/login",
            headers=headers,
            json={"username": "executive", "password": os.environ["REVENUEOS_DEMO_PASSWORD"]},
        )
        response.raise_for_status()
        cookie = dict(client.cookies)
        client.get("/api/dashboard").raise_for_status()

    def request(_: int) -> dict:
        with httpx2.Client(base_url=base, cookies=cookie, timeout=30) as client:
            started = time.perf_counter()
            response = client.get("/api/dashboard")
            correct = (
                response.status_code == 200
                and response.json()["metrics"]["leads"]["inbound_leads"] == 6
            )
            return {
                "status": response.status_code,
                "correct_golden_kpi": correct,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
            }

    with ThreadPoolExecutor(max_workers=5) as pool:
        requests = list(pool.map(request, range(25)))
    report = {
        "evidence_class": "local_synthetic_performance_observation",
        "ranking_leads": len(ids),
        "ranking": results,
        "all_score_explanations_equal": True,
        "api_requests": requests,
        "concurrent_clients": 5,
        "api_fixture_leads": 8,
        "p95_http_ms": percentile([r["elapsed_ms"] for r in requests], 0.95),
        "failures": sum(not r["correct_golden_kpi"] for r in requests),
        "limitations": (
            "Local synthetic environment; reference excludes queue sorting; "
            "three samples, no production SLO or real-user study."
        ),
    }
    Path("outputs/improvements/RevenueOS-Performance.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"failures": report["failures"], "p95_http_ms": report["p95_http_ms"]}))


if __name__ == "__main__":
    main()
