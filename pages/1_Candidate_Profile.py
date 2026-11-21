"""Streamlit multipage view; add to the existing Step 1 app's pages folder."""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from candidate_profile import ProfileValidationError, choose_resume, load_profile, skills_by_evidence

st.set_page_config(page_title="Candidate Profile | AI Job Hunter India", page_icon="👤", layout="wide")
st.title("Candidate Profile")
st.caption("BFSI · Technical Product Owner / Data Product Owner · Technical Business Analyst")

try:
    profile = load_profile()
except (OSError, ValueError, ProfileValidationError) as exc:
    st.error(f"Cannot load candidate profile: {exc}")
    st.stop()

st.subheader(profile["name"])
st.write(profile["professional_headline"])
st.write(profile["experience_summary"])

left, middle, right = st.columns(3)
left.metric("Resume-documented skills", len(skills_by_evidence(profile, "resume_documented")))
middle.metric("Self-reported skills", len(skills_by_evidence(profile, "self_reported")))
right.metric("Match threshold", f"{profile['search_preferences']['minimum_match_score']}%")

st.info("Resume-documented means present in an uploaded resume, not independently verified. Self-reported skills require confirmation before being presented as professional experience.")

po_tab, bsa_tab, skills_tab, history_tab = st.tabs(["Product Owner", "Business Systems Analyst", "Skills & Evidence", "Experience"])
with po_tab:
    st.markdown("**Primary resume: Product Owner / Data Product Owner**")
    for role in profile["target_roles"]["po"]:
        st.write("•", role)
with bsa_tab:
    st.markdown("**Secondary resume: Technical BSA / Systems Analyst**")
    for role in profile["target_roles"]["bsa"]:
        st.write("•", role)
with skills_tab:
    evidence = st.selectbox("Evidence filter", ["All", "resume_documented", "self_reported"])
    rows = profile["skills"] if evidence == "All" else skills_by_evidence(profile, evidence)
    st.dataframe([{"Skill": s["name"], "Category": s["category"], "Evidence": s["evidence"], "Proficiency": s["proficiency"], "Resume sources": ", ".join(s["sources"]) or "—"} for s in rows], use_container_width=True, hide_index=True)
with history_tab:
    st.dataframe(profile["experience"], use_container_width=True, hide_index=True)

st.divider()
st.subheader("Resume selection preview")
job_title = st.text_input("Enter a job title", value="Senior Technical Product Owner - Banking Data")
selected = choose_resume(job_title, profile)
st.success(f"Recommended resume: {'Product Owner / Data Product Owner' if selected == 'po' else 'Technical Business Analyst / BSA'}")
st.caption("Title-based selection is an initial rule. Job-description-aware matching will be implemented in a later step.")

st.subheader("Job search preferences")
search = profile["search_preferences"]
st.write(f"Country: {search['country']} | Cities: {', '.join(search['preferred_cities'])} | Remote India: {'Yes' if search['remote_india'] else 'No'}")
