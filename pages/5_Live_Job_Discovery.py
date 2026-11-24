"""Live ATS discovery, ranking and controlled import."""

import streamlit as st

from core import load_rules, list_jobs
from controlled_import import import_approved

from live_job_connectors import (
    load_live_sources,
    get_enabled_boards,
)

from live_job_ranking import (
    discover_and_rank,
    rank_live_discovery,
)

from smart_discovery import canonical_url


st.set_page_config(
    page_title="Live Job Discovery | AI Job Hunter India",
    layout="wide",
)

st.title("Live Job Discovery")

st.caption(
    "Retrieve real job postings from public ATS APIs, "
    "rank opportunities and approve selected imports. "
    "No automatic applications or database imports."
)


# ----------------------------------------
# SOURCE CONFIGURATION
# ----------------------------------------

try:
    config = load_live_sources()
    boards = get_enabled_boards(config)

except (ValueError, OSError, KeyError) as exc:
    st.error(f"Source configuration error: {exc}")
    st.stop()


board_lookup = {
    board["board_id"]: board
    for board in boards
}

st.subheader("1. Select employer sources")

selected_boards = st.multiselect(
    "Enabled employer boards",
    options=list(board_lookup),
    default=list(board_lookup),
    format_func=lambda board_id: (
        f"{board_lookup[board_id]['company']} "
        f"({board_lookup[board_id]['provider'].title()})"
    ),
    key="live_selected_boards",
)

st.caption(
    f"{len(selected_boards)} of "
    f"{len(boards)} enabled boards selected."
)


# ----------------------------------------
# LIVE DISCOVERY
# ----------------------------------------

if st.button(
    "Discover Live Jobs",
    type="primary",
    disabled=not selected_boards,
):

    for key in (
        "live_report",
        "live_selected_rows",
        "live_confirm_import",
        "live_detail_row",
        "live_import_report",
    ):
        st.session_state.pop(key, None)

    try:
        with st.spinner(
            "Retrieving and ranking live job postings..."
        ):

            report = discover_and_rank(
                config=config,
                board_ids=selected_boards,
            )

            st.session_state["live_report"] = report

    except Exception as exc:
        st.error(f"Discovery failed: {exc}")


report = st.session_state.get("live_report")

if report is None:
    st.info(
        "Select employer boards and click "
        "Discover Live Jobs to begin."
    )
    st.stop()


# ----------------------------------------
# DISCOVERY METRICS
# ----------------------------------------

summary = report["summary"]

st.subheader("2. Discovery execution summary")

columns = st.columns(5)

metrics = [
    ("Successful sources", summary["sources_successful"]),
    ("Failed sources", summary["sources_failed"]),
    ("Total postings", summary["total_jobs"]),
    ("India matches", summary["india_jobs"]),
    ("Role matches", summary["target_role_matches"]),
]

for column, (label, value) in zip(columns, metrics):
    column.metric(label, value)

st.caption(
    "Role matches include excluded, duplicate and "
    "review-required records. They are not necessarily "
    "eligible opportunities."
)

if summary["sources_failed"]:
    st.warning(
        "Some employer sources failed. "
        "Successful source results are retained."
    )

with st.expander("Source execution details"):

    st.dataframe(
        report["sources"],
        hide_index=True,
        width="stretch",
    )

st.caption(
    f"Unknown country: "
    f"{summary['unknown_country_jobs']} | "
    f"India jobs with unknown work mode: "
    f"{summary['india_missing_work_mode']}"
)


# ----------------------------------------
# ELIGIBILITY METRICS
# ----------------------------------------

st.subheader("3. Role-first screening")

screening_columns = st.columns(4)

screening_metrics = [
    (
        "India candidates",
        summary["india_candidates_screened"],
    ),
    (
        "Unrelated roles suppressed",
        summary["suppressed_unrelated_roles"],
    ),
    (
        "Junior roles suppressed",
        summary["suppressed_junior_roles"],
    ),
    (
        "Retained for ranking",
        summary["screening_retained"],
    ),
]

for column, (label, value) in zip(
    screening_columns, screening_metrics
):
    column.metric(label, value)

st.caption(
    "Only recognized target roles that are not "
    "classified as junior or entry-level proceed "
    "to detailed ranking."
)

with st.expander("Suppressed job records"):

    suppressed = [
        {
            "Title": job["title"],
            "Company": job["company"],
            "Location": job["location"],
            "Reason": reason,
        }
        for records, reason in [
            (
                report["suppressed_roles"],
                "Unrelated role",
            ),
            (
                report["suppressed_seniority"],
                "Junior or entry-level",
            ),
        ]
        for job in records
    ]

    if suppressed:
        st.dataframe(
            suppressed,
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No suppressed records.")

st.subheader("4. Eligibility and ranking")

columns = st.columns(5)

decisions = [
    ("Eligible", summary["eligible"]),
    ("Excluded", summary["excluded"]),
    ("Duplicate URL", summary["duplicate_url"]),
    ("Possible duplicate", summary["possible_duplicate"]),
    ("Review", summary["review"]),
]

for column, (label, value) in zip(columns, decisions):
    column.metric(label, value)

results = report["results"]

if not results:
    st.info("No target opportunities survived screening.")
    st.stop()


# ----------------------------------------
# RANKED JOB TABLE
# ----------------------------------------

role_only = st.checkbox(
    "Show target role matches only",
    value=True,
    key="live_role_only",
)

decision_filter = st.multiselect(
    "Filter by eligibility decision",
    options=[
        "Eligible",
        "Review",
        "Excluded",
        "Duplicate URL",
        "Possible duplicate",
    ],
    default=["Eligible", "Review"],
    key="live_decision_filter",
)

minimum_score = st.slider(
    "Minimum relevance score",
    min_value=0,
    max_value=100,
    value=0,
    key="live_minimum_score",
)

visible = [
    job
    for job in report["ranked_results"]
    if (
        not role_only
        or job.get("primary_role")
    )
    and job["decision"] in decision_filter
    and job["relevance_score"] >= minimum_score
]

table_rows = [
    {
        "Row": job["row"],
        "Decision": job["decision"],
        "Score": job["relevance_score"],
        "Recommendation": job["recommendation"],
        "Job Title": job["title"],
        "Company": job["company"],
        "Location": job["location"],
        "Work Mode": job["work_mode"] or "Unknown",
        "Source": job["source_provider"],
        "Role Family": job.get("primary_role") or "",
        "Seniority": job.get("seniority", ""),
        "BFSI Domains": ", ".join(
            job.get("bfsi_domains", [])
        ),
        "Eligibility Reason": job["reason"],
        "Job URL": job["url"],
    }
    for job in visible
]

st.caption(
    f"Displaying {len(visible)} of "
    f"{len(results)} ranked records."
)

if table_rows:

    st.dataframe(
        table_rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Relevance Score",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Job URL": st.column_config.LinkColumn(
                "Job URL",
                display_text="Open posting",
            ),
        },
    )

else:
    st.info(
        "No jobs match the current filters. "
        "Adjust the filters to inspect other records."
    )


# ----------------------------------------
# JOB INSPECTION
# ----------------------------------------

st.subheader("5. Inspect job opportunity")

jobs_by_row = {
    job["row"]: job
    for job in results
}

inspection_rows = [
    job["row"]
    for job in visible
]

if not inspection_rows:
    st.info("No visible jobs to inspect.")
    st.stop()

if st.session_state.get("live_detail_row") not in inspection_rows:
    st.session_state["live_detail_row"] = inspection_rows[0]

detail_row = st.selectbox(
    "Select a job to inspect",
    options=inspection_rows,
    format_func=lambda row: (
        f"Row {row} — "
        f"{jobs_by_row[row]['title']} | "
        f"{jobs_by_row[row]['company']}"
    ),
    key="live_detail_row",
)

job = jobs_by_row[detail_row]

columns = st.columns(3)

columns[0].metric(
    "Relevance score",
    f"{job['relevance_score']:.1f}/100",
)

columns[1].metric(
    "Recommendation",
    job["recommendation"],
)

columns[2].metric(
    "Eligibility",
    job["decision"],
)

st.write("**Eligibility reason:**", job["reason"])
st.write("**Original location:**", job["original_location"])
st.write("**Source board:**", job["source_board_id"])

url = canonical_url(job["url"])

if url:
    st.link_button("Open original job posting", url)

score_tab, evidence_tab, description_tab = st.tabs([
    "Score Breakdown",
    "Classification Evidence",
    "Job Description",
])

with score_tab:

    for dimension, points in job.get(
        "score_breakdown", {}
    ).items():

        maximum = job.get(
            "ranking_weights", {}
        ).get(dimension, 0)

        st.write(
            f"**{dimension.replace('_', ' ').title()}**"
            f" — {points}/{maximum}"
        )

        if maximum:
            st.progress(
                min(max(points / maximum, 0.0), 1.0)
            )

with evidence_tab:

    st.write(
        "**Role family:**",
        job.get("primary_role") or "Unknown",
    )

    st.write(
        "**Seniority:**",
        job.get("seniority", "Unknown"),
    )

    st.write(
        "**Employer category:**",
        job.get("company_category") or "Unknown",
    )

    st.write(
        "**Location status:**",
        job.get("location_status", "Unknown"),
    )

    st.write("**Matched role evidence**")
    st.json(job.get("matched_roles", {}))

    st.write("**BFSI evidence**")
    st.json(job.get("bfsi_evidence", {}))

    st.write("**Technical skill evidence**")
    st.json(job.get("skill_evidence", {}))

with description_tab:

    if job.get("description"):
        st.text(job["description"])

    else:
        st.info(
            "Job description unavailable from source."
        )


# ----------------------------------------
# CONTROLLED IMPORT
# ----------------------------------------

st.subheader("6. Review and approve imports")

eligible = [
    job["row"]
    for job in results
    if job["decision"] == "Eligible"
]

st.caption(
    "Only eligible jobs may be selected. "
    "The import engine revalidates each selected record "
    "against current database contents and business rules."
)

selected_rows = st.multiselect(
    "Select eligible jobs to save",
    options=eligible,
    format_func=lambda row: (
        f"Row {row} — "
        f"{jobs_by_row[row]['title']} | "
        f"{jobs_by_row[row]['company']}"
    ),
    key="live_selected_rows",
)

confirmed = st.checkbox(
    "I reviewed and approve saving these selected jobs.",
    key="live_confirm_import",
)

if st.button(
    "Import selected live jobs",
    type="primary",
    disabled=not selected_rows or not confirmed,
):

    try:

        if len(report["incoming"]) > 1000:
            raise ValueError(
                "Import batch exceeds the existing "
                "1,000-record limit."
            )

        import_report = import_approved(
            report["incoming"],
            selected_rows,
            load_rules(),
        )

        st.session_state[
            "live_import_report"
        ] = import_report

        # Reclassify against the current database.
        # No additional network requests are made.
        discovery = {
            "india_jobs": report["india_candidates"],
            "sources": report["sources"],
            "summary": report["summary"],
        }

        st.session_state["live_report"] = (
            rank_live_discovery(
                discovery,
                existing=list_jobs(),
                rules=load_rules(),
            )
        )

        for key in (
            "live_selected_rows",
            "live_confirm_import",
        ):
            st.session_state.pop(key, None)

        st.rerun()

    except Exception as exc:
        st.error(f"Import or refresh failed: {exc}")
        st.warning(
            "Check saved jobs before retrying."
        )

import_report = st.session_state.get(
    "live_import_report"
)

if import_report:

    st.info("Latest import execution report")

    st.json(import_report)
