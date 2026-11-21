"""Streamlit Step 3: inspect JD, explain evidence and recommend resume."""
import sys
from pathlib import Path
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from candidate_profile import load_profile
from job_matcher import analyze_job

st.set_page_config(page_title='Job Matcher | AI Job Hunter India', page_icon='🎯', layout='wide')
st.title('🎯 Resume-to-Job Matcher')
st.caption('Step 3 · Free, offline, explainable matching · No live job search or automatic application')
try:
    profile = load_profile()
except (OSError, ValueError) as exc:
    st.error(f'Cannot load candidate profile: {exc}')
    st.stop()

st.info('Paste the full job description. Resume-documented means present in your uploaded resume, not independently verified. Self-reported skills receive lower confidence.')
with st.form('job_match'):
    title = st.text_input('Job title', placeholder='e.g., Technical Product Owner — Data Platforms')
    jd = st.text_area('Full job description', height=260, placeholder='Paste the responsibilities, required skills and qualifications here...')
    submitted = st.form_submit_button('Analyze job fit', type='primary')
if submitted:
    try:
        result = analyze_job(title, jd, profile)
        st.session_state['step3_result'] = result
    except (ValueError, TypeError) as exc:
        st.error(str(exc))
if 'step3_result' in st.session_state:
    result = st.session_state['step3_result']
    a,b,c = st.columns(3)
    a.metric('Keyword evidence coverage', f"{result['score']}%")
    b.metric('Recognized requirements', result['requirements_found'])
    c.metric('Suggested resume', 'Technical PO / Data PO' if result['recommended_resume'] == 'po' else 'Technical BSA')
    st.warning(result['warning'])
    st.caption('This is a preliminary keyword coverage score, NOT a probability of getting hired or a complete eligibility assessment.')
    if result['requirements_found']:
        st.dataframe(result['evidence'], use_container_width=True, hide_index=True)
    st.subheader('Interpretation')
    missing = [x['requirement'] for x in result['evidence'] if x['status'] == 'missing']
    uncertain = [x['requirement'] for x in result['evidence'] if x['status'] == 'self_reported']
    st.write('**Not evidenced in profile:**', ', '.join(missing) if missing else 'None among recognized terms')
    st.write('**Self-reported / needs confirmation:**', ', '.join(uncertain) if uncertain else 'None among recognized terms')
    st.caption('This prototype does not yet parse required vs preferred skills, years of experience, location, or salary from free-text descriptions.')
