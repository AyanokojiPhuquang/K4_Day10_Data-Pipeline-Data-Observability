from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build baseline pipeline end-to-end.

    Steps:
    1. Load settings.
    2. Load or fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Create or load evaluation set.
    7. Evaluate.
    8. Run quality checks and freshness report.
    9. Generate markdown report.
    """
    settings = load_settings()
    run_date = now_utc()

    # Step 1: Load or fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("[phase1] Fetching records from source...")
        records = fetch_source_records(settings)
    else:
        print("[phase1] Loading cached raw records...")
        records = load_raw_records(settings.paths.raw_records_json)

    print(f"[phase1] Raw records: {len(records)}")

    # Step 2: Clean data
    df = build_clean_dataframe(records, run_date)
    print(f"[phase1] Cleaned records: {len(df)}")

    # Step 3: Save clean CSV/JSON
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"[phase1] Saved clean data to {settings.paths.clean_csv}")

    # Step 4: Build embedding index
    print("[phase1] Building embedding index...")
    index = LocalEmbeddingIndex.build(
        df, settings, embeddings_output_path=settings.paths.embeddings_json
    )
    print(f"[phase1] Index built with {len(df)} documents.")

    # Step 5: Create or load evaluation set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("[phase1] Generating evaluation test set...")
        build_test_set(df, settings.paths.eval_testset)
    else:
        print("[phase1] Using existing test set.")

    # Step 6: Evaluate
    print("[phase1] Running evaluation...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"[phase1] Baseline metrics: hit_rate={metrics['retrieval_hit_rate']:.4f}, "
          f"f1={metrics['mean_token_f1']:.4f}, "
          f"judge_acc={metrics['judge_accuracy']:.4f}, "
          f"judge_score={metrics['mean_judge_score']:.2f}")

    # Step 7: Quality checks
    print("[phase1] Running quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline_quality")

    # Step 8: Freshness report
    print("[phase1] Building freshness report...")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    # Step 9: Generate report
    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "records_fetched": len(records),
        "records_cleaned": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
    )

    print("[phase1] ✅ Baseline pipeline complete.")
