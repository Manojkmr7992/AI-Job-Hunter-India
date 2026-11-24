"""Step 5.2: preview, select, confirm and import approved eligible CSV jobs."""
import hashlib
import streamlit as st
from core import list_jobs, load_rules
from job_discovery import parse_csv
from smart_discovery import preview_jobs, canonical_url
from controlled_import import import_approved

st.set_page_config(page_title='Smart Discovery | AI Job Hunter India', layout='wide')
st.title('🧭 Step 5.3 — Smart Discovery, BFSI Ranking & Controlled Import')
st.caption('Review CSV job alerts before saving. No automatic applications or portal scraping.')
file = st.file_uploader('Upload a CSV job-alert file', type=['csv'], key='step52_csv')
if file is not None:
    try:
        data = file.getvalue()
        signature = hashlib.sha256(data).hexdigest()
        if st.session_state.get('step52_signature') != signature:
            st.session_state['step52_signature'] = signature
            st.session_state['step52_selected'] = []
            st.session_state.pop('step52_report', None)
            st.session_state.pop('step52_confirm', None)
            st.session_state.pop('weighted_job_details', None)
        incoming = parse_csv(data)
        rules = load_rules()
        results = preview_jobs(incoming, list_jobs(), rules)
        categories = ('Eligible', 'Excluded', 'Duplicate URL', 'Possible duplicate', 'Review')
        columns = st.columns(5)
        for col, category in zip(columns, categories):
            col.metric(category, sum(r['decision'] == category for r in results))
        st.subheader("Weighted Job Relevance Ranking")

        st.caption(
            "Scores are rule-based job relevance indicators, "
            "not resume-match probabilities. Eligibility and "
            "duplicate checks continue to control imports."
        )

        recommendations = (
            "Excellent match",
            "Strong match",
            "Potential match",
            "Manual review",
            "Low relevance",
        )

        ranking_columns = st.columns(5)

        for col, recommendation in zip(
            ranking_columns, recommendations
        ):
            col.metric(
                recommendation,
                sum(
                    r["decision"] == "Eligible"
                    and r["recommendation"] == recommendation
                    for r in results
                ),
            )

        ranked_results = sorted(
            results,
            key=lambda r: (
                r["decision"] != "Eligible",
                -r["relevance_score"],
                r["row"],
            ),
        )

        display_rows = [
            {
                "Row": r["row"],
                "Decision": r["decision"],
                "Score": r["relevance_score"],
                "Recommendation": r["recommendation"],
                "Job Title": r["title"],
                "Company": r["company"],
                "Location": r["location"],
                "Work Mode": r["work_mode"],
                "Role Family": (
                    r.get("primary_role") or "Unclassified"
                ).replace("_", " ").title(),
                "Seniority": r.get(
                    "seniority", "review"
                ).replace("_", " ").title(),
                "BFSI Domains": ", ".join(
                    d.replace("_", " ").title()
                    for d in r.get("bfsi_domains", [])
                ),
                "Technical Skills": ", ".join(
                    s.replace("_", " ").title()
                    for s in r.get("skill_categories", [])
                ),
                "Eligibility Reason": r["reason"],
                "Job URL": r["url"],
            }
            for r in ranked_results
        ]

        st.dataframe(
            display_rows,
            width="stretch",
            hide_index=True,
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

        st.subheader("Individual Job Analysis")

        if ranked_results:
            jobs_by_row = {
                r["row"]: r for r in ranked_results
            }

            selected_job_row = st.selectbox(
                "Select a job to inspect its ranking",
                options=list(jobs_by_row),
                format_func=lambda n: (
                    f"Row {n} | "
                    f"{jobs_by_row[n]['relevance_score']}/100 | "
                    f"{jobs_by_row[n]['title']} | "
                    f"{jobs_by_row[n]['company']}"
                ),
                key="weighted_job_details",
            )

            selected_job = jobs_by_row[selected_job_row]

            st.markdown(
                f"**{selected_job['title']}**"
            )

            st.write(
                f"{selected_job['company']} | "
                f"{selected_job['location']} | "
                f"{selected_job['work_mode']}"
            )

            summary_columns = st.columns(3)

            summary_columns[0].metric(
                "Relevance Score",
                f"{selected_job['relevance_score']:.1f}/100",
            )

            summary_columns[1].metric(
                "Recommendation",
                selected_job["recommendation"],
            )

            summary_columns[2].metric(
                "Import Decision",
                selected_job["decision"],
            )

            st.write(
                "**Eligibility reason:**",
                selected_job["reason"],
            )

            score_tab, evidence_tab, description_tab = st.tabs(
                [
                    "Score Breakdown",
                    "Classification Evidence",
                    "Job Description",
                ]
            )

            with score_tab:
                weights = selected_job["ranking_weights"]
                breakdown = selected_job["score_breakdown"]

                for component, maximum in weights.items():
                    earned = breakdown.get(component, 0)

                    label = component.replace(
                        "_", " "
                    ).title()

                    st.write(
                        f"**{label}:** "
                        f"{earned:.1f}/{maximum}"
                    )

                    st.progress(
                        min(
                            max(earned / maximum, 0.0),
                            1.0,
                        ) if maximum else 0.0
                    )

                st.caption(
                    "Component scores reflect configured "
                    "taxonomy weights and detected evidence."
                )

            with evidence_tab:
                def readable(value):
                    return str(value).replace(
                        "_", " "
                    ).title()

                st.write(
                    "**Primary role:**",
                    readable(
                        selected_job.get("primary_role")
                        or "Unclassified"
                    ),
                )

                st.write(
                    "**Seniority:**",
                    readable(
                        selected_job.get(
                            "seniority", "review"
                        )
                    ),
                )

                st.write(
                    "**Employer category:**",
                    readable(
                        selected_job.get("company_category")
                        or "Unknown employer"
                    ),
                )

                st.write(
                    "**Location classification:**",
                    readable(
                        selected_job.get(
                            "location_status", "review"
                        )
                    ),
                )

                seniority_evidence = selected_job.get(
                    "seniority_evidence", []
                )

                st.write("**Seniority evidence:**")
                st.write(
                    ", ".join(seniority_evidence)
                    or "No explicit evidence detected."
                )

                evidence_groups = (
                    ("Matched Roles", "matched_roles"),
                    ("BFSI Domains", "bfsi_evidence"),
                    ("Technical Skills", "skill_evidence"),
                )

                for heading, field in evidence_groups:
                    st.markdown(f"**{heading}**")

                    evidence = selected_job.get(field, {})

                    if evidence:
                        for category, phrases in evidence.items():
                            st.write(
                                f"{readable(category)}: "
                                + ", ".join(phrases)
                            )
                    else:
                        st.caption(
                            "No matching evidence detected."
                        )

            with description_tab:
                description = selected_job.get(
                    "description", ""
                )

                if description:
                    st.text(description)
                else:
                    st.info(
                        "No job description was supplied. "
                        "Classification uses the available "
                        "job information."
                    )

                st.caption(
                    "Descriptions are available for preview "
                    "but are not yet persisted in the database."
                )

            if canonical_url(selected_job["url"]):
                st.link_button(
                    "Open Original Job Posting",
                    selected_job["url"],
                )

        st.divider()

        eligible = [r['row'] for r in results if r['decision'] == 'Eligible']
        st.write('Only **Eligible** rows may be selected. Possible duplicates and incomplete records are blocked until corrected and re-uploaded.')
        selected = st.multiselect('Select job rows to import', options=eligible,
                                  format_func=lambda n: f"Row {n} — {results[n-1]['title']} | {results[n-1]['company']}",
                                  key='step52_selected')
        confirm = st.checkbox('I reviewed these postings and approve saving the selected jobs',
                              key='step52_confirm')
        if st.button('Import selected jobs into my database', type='primary',
                     disabled=not selected or not confirm):
            # Revalidate each row against current database state on click.
            report = import_approved(incoming, selected, rules)
            st.session_state['step52_report'] = report
            st.rerun()
        report = st.session_state.get('step52_report')
        if report:
            st.success(f"Imported: {report['imported']} | URL duplicates: {report['duplicate_url']} | "
                       f"Possible duplicates: {report['possible_duplicate']} | "
                       f"Excluded: {report['excluded']} | Review: {report['review']} | "
                       f"Not selected: {report['skipped_unselected']}")
            if report['errors']:
                st.error('\n'.join(report['errors'][:20]))
            st.info('Refresh or re-upload to see the latest database classifications.')
    except (ValueError, KeyError, TypeError) as exc:
        st.error(str(exc))
