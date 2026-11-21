# AI Job Hunter India — Step 1

Local Python/Streamlit prototype with SQLite persistence, India location rules, sample postings, and application status tracking.

## Run on macOS

```bash
cd ~/Documents/AI-Job-Hunter-India
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Then open the local Streamlit URL (usually http://localhost:8501).

To get started, click **Load fictional demo jobs** in the sidebar. Modify `rules.json` to change your target titles and locations, then restart the app.

This prototype does not access LinkedIn, scrape sites, or automatically apply to jobs. It uses sample jobs on example.com, which are not real openings.
