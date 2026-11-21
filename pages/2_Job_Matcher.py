"""Step 5.4: explainable candidate-to-job matching interface."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from candidate_profile import load_profile
from job_matcher import analyze_job


st.set_page_config(
    page_title="Job Matcher | AI Job Hunter India",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Enhanced Job Description Matcher")

st.caption(
    "Step 5.4 | Offline, rule-based candidate matching | "
    "No automatic applications"
)

try:
    profile = load_profile()
except (OSError, ValueError) as exc:
    st.error(f"Cannot load candidate profile: {exc}")
    st.stop()

st.info(
    "Paste a complete job description. The system identifies known "
    "skills, classifies explicit requirement sections, and compares "
    "them against your candidate profile."
)

with st.form("enhanced_job_match"):
    title = st.text_input(
        "Job title",
        placeholder="Technical Product Owner - Data Platforms",
    )

    jd = st.text_area(
        "Full job description",
        height=300,
        placeholder=(
            "Required Qualifications:\n"
            "- SQL\n"
            "- Python\n\n"
            "Preferred Qualifications:\n"
            "- Snowflake\n"
            "- AWS"
        ),
    )

    submitted = st.form_submit_button(
        "Analyze job fit",
        type="primary",
    )

if submitted:
    # Clear previous results so failed submissions cannot
    # accidentally display an earlier job's analysis.
    st.session_state.pop("step3_result", None)

    try:
        st.session_state["step3_result"] = analyze_job(
            title, jd, profile
        )
    except (ValueError, TypeError) as exc:
        st.error(str(exc))

if "step3_result" in st.session_state:
    result = st.session_state["step3_result"]

    st.divider()
    st.subheader("📊 Job Match Summary")
    st.write(f"**Job:** {result['job_title']}")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Original coverage",
        f"{result['score']}%",
    )

    col2.metric(
        "Weighted coverage",
        f"{result['weighted_score']}%",
    )

    col3.metric(
        "Requirements detected",
        result["requirements_found"],
    )

    resume_name = (
        "Technical PO / Data PO"
        if result["recommended_resume"] == "po"
        else "Technical BSA"
    )

    col4.metric("Suggested resume", resume_name)

    st.progress(
        min(max(result["weighted_score"], 0), 100) / 100
    )

    st.caption(
        "Weighted coverage gives greater importance to explicitly "
        "required skills. It is not a hiring probability or a "
        "complete eligibility assessment."
    )

    st.warning(result["warning"])

    st.divider()
    st.subheader("📋 Qualification Breakdown")

    evidence = result["enhanced_evidence"]

    if evidence:
        rows = []

        for item in evidence:
            rows.append({
                "Skill / Requirement": item["requirement"],
                "JD Classification": item["classification"].title(),
                "Evidence Source": item["status"].replace(
                "_", " "
                 ).title(),
            "Proficiency / Evidence Details": item["detail"],
            })

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No recognized requirements were found. "
            "The score is not meaningful for this description."
        )

    st.divider()
    st.subheader("🚨 Required Qualification Gaps")

    missing_required = result["missing_required"]

    if missing_required:
        st.error(
            "The following required skills are not documented "
            "in your candidate profile:"
        )

        for skill in missing_required:
            st.write(f"- {skill}")

        st.caption(
            "A missing profile entry does not necessarily mean "
            "you lack the skill. Verify your experience before "
            "making an application decision."
        )
    else:
        st.success(
            "No missing explicitly required skills were detected "
            "among the recognized requirements."
        )

    st.divider()
    st.subheader("🔎 Additional Skill Analysis")

    missing = [
        item["requirement"]
        for item in evidence
        if item["status"] == "missing"
    ]

    self_reported = [
        item["requirement"]
        for item in evidence
        if item["status"] == "self_reported"
    ]

    st.write(
        "**All skills not documented in profile:**",
        ", ".join(missing) if missing else "None detected",
    )

    st.write(
        "**Self-reported skills requiring confirmation:**",
        ", ".join(self_reported)
        if self_reported else "None detected",
    )

    st.divider()
    st.subheader("🧠 How This Analysis Works")

    with st.expander("View scoring methodology"):
        st.markdown(
            """
            **Requirement importance**

            - Required: 3 points
            - Preferred: 1 point
            - Unspecified: 1 point

            **Candidate evidence confidence**

            - Resume documented: 100%
            - Self-reported: 25%
            - Missing: 0%

            **Limitations**

            - Uses recognized keywords and aliases.
            - Requirement classification relies on explicit
              job-description section headings.
            - Does not perform AI semantic analysis.
            - Does not infer years of experience, salary,
              work authorization, or full job eligibility.
            - Missing requirements must be reviewed manually.
            """
        )
