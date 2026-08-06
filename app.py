from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


# Page Configuration following Streamlit official best practices
st.set_page_config(
    page_title="Day 10 - Data pipeline & observability dashboard",
    page_icon=":material/database:",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_cached_settings():
    return load_settings()


@st.cache_resource
def get_cached_index(settings, embeddings_path: Path):
    return LocalEmbeddingIndex.load(settings=settings, embeddings_path=embeddings_path)


settings = get_cached_settings()

# Sidebar Setup
with st.sidebar:
    st.title(":material/database: Data observability & RAG")
    st.caption("Day 10 Data Pipeline & RAG Lifecycle")
    st.divider()

    st.markdown("### Vector collection")
    active_dataset_option = st.segmented_control(
        "Vector collection",
        options=["Baseline", "Corrupted", "Repaired"],
        default="Baseline",
        label_visibility="collapsed",
    )

    collection_map = {
        "Baseline": (settings.baseline_collection_name, settings.paths.embeddings_json, settings.paths.clean_csv),
        "Corrupted": (settings.corrupted_collection_name, settings.paths.corrupted_embeddings_json, settings.paths.corrupted_clean_csv),
        "Repaired": (settings.repaired_collection_name, settings.paths.repaired_embeddings_json, settings.paths.repaired_clean_csv),
    }

    current_coll_name, current_emb_path, current_csv_path = collection_map[active_dataset_option]

    with st.container(border=True):
        st.markdown("**Configuration**")
        st.caption(f"LLM provider: `{settings.llm_provider}`")
        st.caption(f"Embedding model: `{settings.embedding_model}`")
        st.caption(f"Active collection: `{current_coll_name}`")

# Header Title with Sentence Casing and Material Symbols
st.title(":material/analytics: Data pipeline & observability RAG dashboard")
st.caption("End-to-end data lifecycle: Ingestion ➔ Cleaning ➔ Indexing ➔ Observability ➔ Corruption ➔ Repair")

# Multi-tab layout
tab_chat, tab_observability, tab_pipeline, tab_dataset = st.tabs([
    "Q&A assistant",
    "Observability & metrics",
    "Pipeline control panel",
    "Dataset explorer",
])

# ==========================================
# TAB 1: CONVERSATIONAL CHAT UI (Official st.chat_message pattern)
# ==========================================
with tab_chat:
    st.subheader(":material/chat: Ask questions about the paper corpus")

    # Initialize chat message history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display suggestion chips when chat history is empty
    SUGGESTIONS = {
        ":blue[:material/help:] RAG papers": "What papers discuss retrieval augmented generation?",
        ":green[:material/person:] Author query": "Who authored the top retrieval papers?",
        ":orange[:material/calendar_today:] Publication dates": "When were the papers published?",
    }

    if not st.session_state.messages:
        selected_suggestion = st.pills(
            "Try asking:",
            list(SUGGESTIONS.keys()),
            label_visibility="collapsed",
        )
        if selected_suggestion:
            prompt = SUGGESTIONS[selected_suggestion]
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

    # Render previous conversation history
    for msg in st.session_state.messages:
        avatar_icon = ":material/person:" if msg["role"] == "user" else ":material/smart_toy:"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])
            if "retrieved" in msg:
                with st.expander("View retrieved contexts"):
                    for idx, (doc_id, title, ctx) in enumerate(zip(msg["retrieved"]["ids"], msg["retrieved"]["titles"], msg["retrieved"]["contexts"]), 1):
                        st.markdown(f"**[{idx}] {title}** (DOI: `{doc_id}`)")
                        st.text(ctx)

    # Chat input control
    if user_prompt := st.chat_input("Ask a question about the indexed corpus..."):
        # Append user message
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(user_prompt)

        # Process assistant answer
        with st.chat_message("assistant", avatar=":material/smart_toy:"):
            if not current_emb_path.exists():
                err_msg = f"Vector index for `{active_dataset_option}` collection not found. Please run the pipeline in the Pipeline control panel first."
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
            else:
                with st.spinner("Searching ChromaDB index..."):
                    index = get_cached_index(settings=settings, embeddings_path=current_emb_path)
                    result = answer_question(user_prompt, settings=settings, index=index)

                st.markdown(result.answer)
                with st.expander("View retrieved contexts"):
                    for idx, (doc_id, title, ctx) in enumerate(zip(result.retrieved_doc_ids, result.retrieved_titles, result.retrieved_contexts), 1):
                        st.markdown(f"**[{idx}] {title}** (DOI: `{doc_id}`)")
                        st.text(ctx)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.answer,
                    "retrieved": {
                        "ids": result.retrieved_doc_ids,
                        "titles": result.retrieved_titles,
                        "contexts": result.retrieved_contexts,
                    },
                })

# ==========================================
# TAB 2: DATA OBSERVABILITY & METRICS DASHBOARD
# ==========================================
with tab_observability:
    st.subheader(":material/analytics: Performance & quality signals")

    # Load baseline, corrupted, repaired metrics
    b_metrics = read_json(settings.paths.baseline_metrics) if settings.paths.baseline_metrics.exists() else {}
    c_metrics = read_json(settings.paths.corrupted_metrics) if settings.paths.corrupted_metrics.exists() else {}
    r_metrics = read_json(settings.paths.repaired_metrics) if settings.paths.repaired_metrics.exists() else {}

    # Active collection metrics
    active_metrics = b_metrics if active_dataset_option == "Baseline" else (c_metrics if active_dataset_option == "Corrupted" else r_metrics)


    def get_delta_str(key: str, is_pct: bool = False, precision: int = 4) -> str | None:
        if active_dataset_option == "Baseline" or not b_metrics or not active_metrics:
            return None
        val = active_metrics.get(key, 0.0)
        base_val = b_metrics.get(key, 0.0)
        diff = val - base_val
        if is_pct:
            return f"{diff:+.2%} vs Baseline"
        return f"{diff:+.{precision}f} vs Baseline"

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        with st.container(border=True):
            st.metric(
                label="Retrieval hit rate",
                value=f"{active_metrics.get('retrieval_hit_rate', 0.0):.2%}" if active_metrics else "N/A",
                delta=get_delta_str("retrieval_hit_rate", is_pct=True),
            )
    with col_m2:
        with st.container(border=True):
            st.metric(
                label="Mean token F1",
                value=f"{active_metrics.get('mean_token_f1', 0.0):.4f}" if active_metrics else "N/A",
                delta=get_delta_str("mean_token_f1", precision=4),
            )
    with col_m3:
        with st.container(border=True):
            st.metric(
                label="LLM judge accuracy",
                value=f"{active_metrics.get('judge_accuracy', 0.0):.2%}" if active_metrics else "N/A",
                delta=get_delta_str("judge_accuracy", is_pct=True),
            )
    with col_m4:
        with st.container(border=True):
            st.metric(
                label="Mean judge score",
                value=f"{active_metrics.get('mean_judge_score', 0.0):.2f}" if active_metrics else "N/A",
                delta=get_delta_str("mean_judge_score", precision=2),
            )


    st.divider()

    col_q_check, col_fresh = st.columns(2)

    with col_q_check:
        with st.container(border=True):
            st.markdown("### Data quality checks", help="Automated validation checks")
            q_name = 'baseline_quality_checks' if active_dataset_option == 'Baseline' else ('corrupted_quality_checks' if active_dataset_option == 'Corrupted' else 'repaired_quality_checks')
            q_path = settings.paths.quality_dir / f"{q_name}.json"
            
            if q_path.exists():
                q_data = read_json(q_path)
                status_icon = ":material/check_circle:" if q_data.get('overall_passed') else ":material/error:"
                st.markdown(f"Status: **{status_icon} {'PASSED' if q_data.get('overall_passed') else 'FAILED'}** ({q_data.get('passed_count')}/{len(q_data.get('checks', []))} checks passed)")
                
                checks_df = pd.DataFrame([
                    {
                        "Check": c["check"],
                        "Status": "PASSED" if c["passed"] else "FAILED",
                        "Description": c["description"],
                    }
                    for c in q_data.get("checks", [])
                ])
                st.dataframe(checks_df)
            else:
                st.info("No quality checks report found for this collection.")

    with col_fresh:
        with st.container(border=True):
            st.markdown("### Data freshness monitoring", help="Publication date threshold check")
            f_path = settings.paths.freshness_report if active_dataset_option == "Baseline" else settings.paths.quality_dir / ("corrupted_freshness_report.json" if active_dataset_option == "Corrupted" else "repaired_freshness_report.json")
            if f_path.exists():
                f_data = read_json(f_path)
                fresh_icon = ":material/verified:" if f_data.get("is_fresh") else ":material/warning:"
                st.markdown(f"Freshness status: **{fresh_icon} {'FRESH' if f_data.get('is_fresh') else 'STALE'}**")
                st.json(f_data)
            else:
                st.info("No freshness report found for this collection.")

# ==========================================
# TAB 3: PIPELINE CONTROL PANEL
# ==========================================
with tab_pipeline:
    st.subheader(":material/tune: Pipeline control panel")

    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
        with st.container(border=True):
            st.markdown("#### Phase 1 — Baseline")
            st.caption("Fetch Crossref API ➔ Clean ➔ Index ➔ Evaluate")
            if st.button("Run Phase 1 baseline", icon=":material/play_arrow:"):
                with st.spinner("Executing Phase 1 Baseline..."):
                    records = fetch_source_records(settings) if (settings.refresh_source or not settings.paths.raw_records_json.exists()) else load_raw_records(settings.paths.raw_records_json)
                    clean_df = build_clean_dataframe(records, run_date=pd.Timestamp.now())
                    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
                    eval_bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset, settings.paths.baseline_metrics, settings.paths.baseline_answers)
                    q_res = run_data_quality_checks(clean_df, settings, "baseline_quality_checks")
                    f_res = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
                    generate_phase1_report(settings.paths.baseline_report, {"source_api": settings.source_api, "source_query": settings.source_query, "source_filter": settings.source_filter, "records_count": len(clean_df)}, eval_bundle.summary, q_res, f_res)
                    get_cached_index.clear()
                st.success("Phase 1 baseline completed successfully!")

    with col_p2:
        with st.container(border=True):
            st.markdown("#### Phase 2A — Corruption")
            st.caption("Apply 10 corruption scenarios ➔ Re-evaluate")
            if st.button("Simulate corruption", icon=":material/bug_report:"):
                if not settings.paths.clean_csv.exists():
                    st.error("Please run Phase 1 baseline first.")
                else:
                    with st.spinner("Simulating data corruption & re-evaluating..."):
                        b_df = pd.read_csv(settings.paths.clean_csv)
                        c_df = corrupt_clean_dataframe(b_df, settings.paths.corruption_log)
                        c_index = LocalEmbeddingIndex.build(c_df, settings, settings.paths.corrupted_embeddings_json)
                        c_eval = evaluate_pipeline(settings, c_index, settings.paths.eval_testset, settings.paths.corrupted_metrics, settings.paths.corrupted_answers)
                        run_data_quality_checks(c_df, settings, "corrupted_quality_checks")
                        build_freshness_report(c_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json")
                        get_cached_index.clear()
                    st.warning("Data corruption simulation completed! Alerts triggered.")

    with col_p3:
        with st.container(border=True):
            st.markdown("#### Phase 2B — Repair")
            st.caption("Re-ingest from raw snapshot ➔ Re-evaluate")
            if st.button("Trigger data repair", icon=":material/build:"):
                if not settings.paths.raw_records_json.exists():
                    st.error("Raw records snapshot from Phase 1 required.")
                else:
                    with st.spinner("Repairing dataset from raw snapshot..."):
                        raw_recs = load_raw_records(settings.paths.raw_records_json)
                        r_df = build_clean_dataframe(raw_recs, run_date=pd.Timestamp.now())
                        r_index = LocalEmbeddingIndex.build(r_df, settings, settings.paths.repaired_embeddings_json)
                        r_eval = evaluate_pipeline(settings, r_index, settings.paths.eval_testset, settings.paths.repaired_metrics, settings.paths.repaired_answers)
                        r_q = run_data_quality_checks(r_df, settings, "repaired_quality_checks")
                        r_f = build_freshness_report(r_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json")
                        generate_corruption_report(
                            settings.paths.comparison_report,
                            read_json(settings.paths.baseline_metrics),
                            read_json(settings.paths.corrupted_metrics) if settings.paths.corrupted_metrics.exists() else r_eval.summary,
                            r_eval.summary,
                            read_json(settings.paths.quality_dir / "corrupted_quality_checks.json") if (settings.paths.quality_dir / "corrupted_quality_checks.json").exists() else r_q,
                            r_q,
                            read_json(settings.paths.quality_dir / "corrupted_freshness_report.json") if (settings.paths.quality_dir / "corrupted_freshness_report.json").exists() else r_f,
                            r_f,
                        )
                        get_cached_index.clear()
                    st.success("Data repair completed successfully! Baseline metrics restored.")

# ==========================================
# TAB 4: DATASET EXPLORER
# ==========================================
with tab_dataset:
    st.subheader(f":material/folder: Dataset explorer ({active_dataset_option})")
    if current_csv_path.exists():
        df_view = pd.read_csv(current_csv_path)
        st.caption(f"Total rows: `{len(df_view)}` | Columns: `{', '.join(df_view.columns)}`")
        st.dataframe(df_view)
    else:
        st.info("No CSV file available for this collection.")
