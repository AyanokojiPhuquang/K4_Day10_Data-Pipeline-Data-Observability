from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build corruption -> evaluate -> repair -> compare flow.

    Steps:
    1. Load baseline metrics and clean dataset.
    2. Create corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index and evaluate.
    5. Run quality checks/freshness on corrupted data.
    6. Repair from raw records.
    7. Evaluate repaired dataset.
    8. Generate comparison report.
    """
    settings = load_settings()
    run_date = now_utc()

    # Step 1: Load baseline
    print("[corruption_flow] Loading baseline data...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.read_csv(settings.paths.clean_csv)

    # Ensure list columns are properly loaded
    import ast
    for col in ("authors", "categories"):
        if col in baseline_df.columns:
            baseline_df[col] = baseline_df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else x
            )

    # Step 2: Corrupt data
    print("[corruption_flow] Applying corruption...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)

    # Step 3: Save corrupted artifacts
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"[corruption_flow] Corrupted data saved ({len(corrupted_df)} records).")

    # Step 4: Rebuild index and evaluate corrupted
    print("[corruption_flow] Building corrupted index...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )

    print("[corruption_flow] Evaluating corrupted data...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary

    # Step 5: Quality checks on corrupted
    print("[corruption_flow] Quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)

    # Step 6: Repair from raw records
    print("[corruption_flow] Repairing from raw source...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"[corruption_flow] Repaired data saved ({len(repaired_df)} records).")

    # Step 7: Rebuild index and evaluate repaired
    print("[corruption_flow] Building repaired index...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )

    print("[corruption_flow] Evaluating repaired data...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary

    # Quality checks on repaired
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)

    # Step 8: Generate comparison report
    print("[corruption_flow] Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # Print summary
    print("\n[corruption_flow] === COMPARISON SUMMARY ===")
    for metric in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        b = baseline_metrics.get(metric, 0)
        c = corrupted_metrics.get(metric, 0)
        r = repaired_metrics.get(metric, 0)
        print(f"  {metric}: baseline={b:.4f} | corrupted={c:.4f} | repaired={r:.4f}")

    print("\n[corruption_flow] ✅ Corruption flow complete.")
