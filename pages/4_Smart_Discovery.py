"""Step 5.2: preview, select, confirm and import approved eligible CSV jobs."""
import hashlib
import streamlit as st
from core import list_jobs, load_rules
from job_discovery import parse_csv
from smart_discovery import preview_jobs
from controlled_import import import_approved
from bfsi_filter import assess_job

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
        incoming = parse_csv(data)
        rules = load_rules()
        results = preview_jobs(incoming, list_jobs(), rules)
        categories = ('Eligible', 'Excluded', 'Duplicate URL', 'Possible duplicate', 'Review')
        columns = st.columns(5)
        for col, category in zip(columns, categories):
            col.metric(category, sum(r['decision'] == category for r in results))
        enriched = []
        for result in results:
            assessment = assess_job(result, rules)
            enriched.append({**result, 'match_score': assessment['score'],
                             'match_tier': assessment['match_tier'],
                             'match_reasons': '; '.join(assessment['reasons'])})
        st.caption('Ranking is advisory. Eligibility and duplicate checks still control imports. '
                   'Scores use available title/company text; CSV imports do not contain job descriptions.')
        tiers = st.columns(3)
        for col, tier in zip(tiers, ('High match', 'Good match', 'Low evidence')):
            col.metric(tier, sum(r['decision'] == 'Eligible' and r['match_tier'] == tier
                                 for r in enriched))
        st.dataframe(enriched, width='stretch', hide_index=True)

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
