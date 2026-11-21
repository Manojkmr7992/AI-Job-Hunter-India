"""Streamlit UI: python -m streamlit run app.py"""
import streamlit as st
from core import SAMPLE_JOBS, add_job, evaluate, init_db, list_jobs, load_rules, update_status

st.set_page_config(page_title="AI Job Hunter India", page_icon="🎯", layout="wide")
init_db()
rules = load_rules()
st.title("🎯 AI Job Hunter India")
st.caption("Step 1: local prototype · no live job search or automatic submissions")
with st.sidebar:
    st.header("Search preferences")
    st.write("**Country:**", rules["country"])
    st.write("**Cities:**", ", ".join(rules["cities"]))
    st.write("**Remote India:**", "Yes" if rules["allow_remote_india"] else "No")
    st.write("**Target roles:**")
    for title in rules["target_titles"]:
        st.write("•", title)
    if st.button("Load fictional demo jobs"):
        for job in SAMPLE_JOBS:
            add_job(job)
        st.success("Demo jobs loaded (duplicates updated)")

jobs = list_jobs()
results = [(job, *evaluate(job, rules)) for job in jobs]
qualified = sum(ok for _, ok, _ in results)
a, b, c = st.columns(3)
a.metric("Saved jobs", len(jobs))
b.metric("Qualified", qualified)
c.metric("Applied", sum(job["status"] == "applied" for job in jobs))
st.subheader("Job queue")
show_only = st.checkbox("Show only qualified jobs", value=False)
for job, ok, reason in results:
    if show_only and not ok:
        continue
    with st.container(border=True):
        st.markdown(f"**{job['title']}** — {job['company']}")
        st.write(f"{job['location']}, {job['country']} · {job['work_mode']} · {'✅ Qualified' if ok else '❌ Excluded'}: {reason}")
        st.link_button("Open posting", job["url"])
        options = ["discovered", "applied", "interview", "offer", "rejected", "skipped"]
        chosen = st.selectbox("Application status", options, index=options.index(job["status"]), key=f"status_{job['id']}")
        if chosen != job["status"] and st.button("Save status", key=f"save_{job['id']}"):
            update_status(job["id"], chosen)
            st.rerun()
if not jobs:
    st.info("No jobs yet. Click 'Load fictional demo jobs' in the sidebar.")
st.subheader("Add a job manually")
with st.form("new_job"):
    url = st.text_input("Posting URL")
    title = st.text_input("Job title")
    company = st.text_input("Company")
    location = st.text_input("City", value="Bengaluru")
    country = st.text_input("Country", value="India")
    work_mode = st.selectbox("Work mode", ["Hybrid", "Remote", "Onsite"])
    if st.form_submit_button("Save job"):
        try:
            add_job(dict(url=url, title=title, company=company, location=location, country=country, work_mode=work_mode))
            st.success("Job saved")
            st.rerun()
        except ValueError as error:
            st.error(str(error))
