"""Streamlit Step 4 job ingestion interface."""
import csv
import io
import streamlit as st
from core import load_rules
from job_discovery import FIELDS, greenhouse_jobs, import_jobs, parse_csv

st.set_page_config(page_title='Job Discovery | AI Job Hunter India', layout='wide')
st.title('🔎 Step 4 — Job Discovery')
st.caption('CSV job alerts and public company job-board feeds. No credentials, scraping, or auto-apply.')
rules = load_rules()

st.subheader('1. Import Naukri / Indeed alert jobs using CSV')
st.write('Use a CSV with these columns: ' + ', '.join(FIELDS))
sample = io.StringIO()
writer = csv.DictWriter(sample, fieldnames=FIELDS)
writer.writeheader()
writer.writerow({'url':'https://example.com/example-job', 'title':'Technical Product Owner',
                 'company':'Example Company', 'location':'Bengaluru', 'country':'India', 'work_mode':'Hybrid'})
st.download_button('Download CSV template (fictional example)', sample.getvalue(),
                   file_name='job_import_template.csv', mime='text/csv')
file = st.file_uploader('Upload CSV of job postings', type=['csv'])
qualified_only = st.checkbox('Import only roles matching my India preferences', value=True)
if file is not None:
    try:
        jobs = parse_csv(file.getvalue())
        st.write(f'{len(jobs)} rows found')
        st.dataframe(jobs[:25], width='stretch')
        if st.button('Import CSV jobs', type='primary'):
            result = import_jobs(jobs, rules, qualified_only=qualified_only)
            st.success(f"Saved or updated: {result['saved_or_updated']} | Excluded: {result['excluded']} | Duplicates in CSV: {result['duplicates_in_file']}")
            if result['errors']:
                st.warning('\n'.join(result['errors'][:20]))
    except ValueError as exc:
        st.error(str(exc))

st.divider()
st.subheader('2. Discover jobs through a public Greenhouse company board')
st.write('Enter a company’s **Greenhouse board token** (not a login or account name). Review the returned records before importing.')
token = st.text_input('Greenhouse board token', placeholder='company-board-token')
if st.button('Fetch public company openings'):
    try:
        st.session_state['greenhouse_results'] = greenhouse_jobs(token.strip())
    except Exception as exc:
        st.error(f'Could not retrieve board: {exc}')
results = st.session_state.get('greenhouse_results', [])
if results:
    st.info(f'{len(results)} openings retrieved. Greenhouse location strings and work modes need human review; no automatic import from this feed.')
    st.dataframe([{k: item.get(k, '') for k in ('title','company','location','url')} for item in results], width='stretch')
    st.write('Copy relevant jobs into the CSV template, verify country, city, and work mode, then import above.')
