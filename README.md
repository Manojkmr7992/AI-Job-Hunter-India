# AI Job Hunter India

**A Python and Streamlit-based job discovery, filtering, matching, and application tracking platform for BFSI and technical product leadership opportunities in India.**

**Current Release:** Step 5.3 — Smart Discovery, BFSI Ranking & Controlled Import  
**Status:** Local development prototype  
**Technology:** Python · Streamlit · PostgreSQL · SQLite · SQLAlchemy · Pytest

---

## 1. Project Overview

AI Job Hunter India is a modular application designed to organize job opportunities, evaluate their relevance against configurable career preferences, identify duplicate postings, and maintain a structured job application pipeline.

The project focuses on roles including:

- Technical Product Owner / Senior Product Owner
- Technical Product Manager
- Data Product Manager
- AI Product Manager
- Related banking and financial services product roles

The application prioritizes opportunities in Bengaluru, Hyderabad, and Pune, along with eligible remote roles based in India.

**Design principle:** Job discovery and ranking should be explainable, reviewable, and controlled by the user before records are saved.

## 2. Key Features

### Candidate Profile Management

- Maintain a structured local candidate profile.
- Capture career information used by the matching workflow.
- Support profile-driven job relevance evaluation.
- Store personal candidate information locally.

### Job Matching

- Compare job-related information against candidate profile signals.
- Generate keyword-based matching feedback.
- Support manual evaluation of potential opportunities.

### Job Discovery

- Import job alerts from CSV files.
- Preview public Greenhouse job-feed results.
- Normalize selected job fields.
- Apply configurable role and location eligibility rules.

### Smart Discovery and Deduplication

- Classify incoming records as Eligible, Excluded, Duplicate URL, Possible duplicate, or Review.
- Identify repeated URLs and potentially overlapping postings.
- Separate preview and validation from database persistence.

### BFSI Relevance Ranking — Step 5.3

- Calculate deterministic relevance scores from available job information.
- Evaluate BFSI, technical/data, seniority, and location signals.
- Assign High match, Good match, Low evidence, or Excluded categories.
- Provide reasons explaining the assigned ranking.

Ranking is advisory. It does not override eligibility or duplicate controls.

**Current limitation:** CSV-based ranking uses available fields such as title and company rather than full job descriptions. The scoring algorithm is rule-based, not a trained machine-learning model.

### Controlled Job Import

- Allow explicit selection of eligible postings.
- Require user confirmation before importing.
- Revalidate records before saving.
- Persist approved records to the configured database.

### Application Tracking

Track job applications using the following statuses:

`discovered` → `applied` → `interview` → `offer`

Other supported outcomes include `rejected` and `skipped`.

## 3. System Architecture

```text
                  JOB INPUT SOURCES
          ┌──────────────┬───────────────┐
          │ Manual Entry │ CSV Job Alerts│
          └──────┬───────┴──────┬────────┘
                 │              │
                 ▼              ▼
              NORMALIZATION & VALIDATION
                         │
                         ▼
               ELIGIBILITY FILTERING
             (Role / Location / Country)
                         │
                         ▼
               SMART DEDUPLICATION
              (URL / Semantic Signals)
                         │
                         ▼
                BFSI MATCH RANKING
               (Rule-Based Scoring)
                         │
                         ▼
                STREAMLIT PREVIEW
                         │
                         ▼
              USER APPROVAL REQUIRED
                         │
                         ▼
                 CONTROLLED IMPORT
                         │
                         ▼
                PERSISTENCE LAYER
                  ┌──────┴──────┐
                  │             │
              PostgreSQL     SQLite
                  │             │
                  └──────┬──────┘
                         ▼
                JOB TRACKING DASHBOARD
```

Public Greenhouse feed preview is also supported in the discovery module. It does not constitute unrestricted job-board scraping.

## 4. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Programming language | Python | Application and business logic |
| User interface | Streamlit | Interactive dashboard |
| Primary configured database | PostgreSQL | Persistent job records |
| Alternative database | SQLite | Local lightweight persistence |
| Database connectivity | SQLAlchemy / Psycopg | PostgreSQL integration |
| Configuration | python-dotenv / JSON | Environment and business rules |
| Testing | Pytest | Automated regression tests |
| Source control | Git / GitHub | Version history and collaboration |

## 5. Project Structure

```text
ai_job_hunter_step1/
├── app.py
├── core.py
├── postgres_store.py
├── candidate_profile.py
├── job_matcher.py
├── job_discovery.py
├── smart_discovery.py
├── controlled_import.py
├── bfsi_filter.py
├── migrate_sqlite_to_postgres.py
│
├── pages/
│   ├── 1_Candidate_Profile.py
│   ├── 2_Job_Matcher.py
│   ├── 3_Job_Discovery.py
│   └── 4_Smart_Discovery.py
│
├── test_bfsi_filter.py
├── test_candidate_profile.py
├── test_controlled_import.py
├── test_core.py
├── test_job_discovery.py
├── test_job_matcher.py
├── test_smart_discovery.py
│
├── requirements.txt
├── rules.json
├── .env.example
├── .gitignore
└── README.md
```

## 6. Local Installation

### Prerequisites

- Python 3 with virtual environment support
- Git
- PostgreSQL if using the PostgreSQL backend

### Clone the repository

```bash
git clone https://github.com/Manojkmr7992/AI-Job-Hunter-India.git
cd AI-Job-Hunter-India
```

For a private repository, GitHub authentication and repository access are required.

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Configure the database

Copy the environment template:

```bash
cp .env.example .env
```

For SQLite, configure:

```dotenv
JOB_HUNTER_DB=sqlite
```

For PostgreSQL, create the required local database and database user, then configure:

```dotenv
JOB_HUNTER_DB=postgres
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_URL_ENCODED_PASSWORD@127.0.0.1:5432/YOUR_DATABASE
```

The application initializes the required jobs table through its database initialization logic.

**Never commit `.env` or real credentials to GitHub.**

### Launch Streamlit

```bash
python -m streamlit run app.py
```

Open the local URL displayed in Terminal, commonly `http://localhost:8501`.

## 7. Configurable Search Preferences

The `rules.json` file defines the supported search preferences.

Example:

```json
{
  "country": "India",
  "cities": ["Bengaluru", "Hyderabad", "Pune"],
  "allow_remote_india": true,
  "target_titles": [
    "Product Owner",
    "Technical Product Owner",
    "Senior Product Owner",
    "Technical Product Manager",
    "Data Product Manager",
    "AI Product Manager"
  ]
}
```

Update these settings to change the role and location eligibility rules.

## 8. CSV Job Import

The CSV parser requires the following columns:

```csv
url,title,company,location,country,work_mode
```

Example fictional record:

```csv
https://example.com/jobs/demo-001,Technical Product Owner,Demo Bank,Bengaluru,India,Hybrid
```

Supported work modes include Remote, Hybrid, and Onsite.

The import process includes:

1. Upload a UTF-8 CSV file.
2. Validate and normalize records.
3. Review eligibility and duplicate classifications.
4. Inspect BFSI relevance scores and explanations.
5. Select eligible jobs.
6. Explicitly approve the import.
7. Save approved jobs to the configured database.

The CSV parser enforces a 3 MB upload limit and a maximum of 1,000 job rows.

## 9. Automated Testing

Run the complete test suite:

```bash
python -m pytest -q
```

**Latest locally verified result:** 46 tests passed (November 21, 2026).

Tests cover core application behavior, candidate profiles, job matching, job discovery, smart discovery, controlled imports, and BFSI filtering.

This result reflects the locally tested Step 5.3 version; future changes should be validated through regression testing.

## 10. Database Migration

The project includes a one-time SQLite-to-PostgreSQL migration utility:

```bash
python migrate_sqlite_to_postgres.py
```

This runs a dry-run check when the PostgreSQL backend is configured.

To execute the migration:

```bash
python migrate_sqlite_to_postgres.py --apply
```

The migration utility creates a SQLite backup and performs a post-migration verification.

**Before migrating:** Back up your data and verify that the destination PostgreSQL database is configured correctly.

## 11. Security and Privacy

The repository is intended to contain source code and safe configuration templates.

The following must remain outside version control:

- Database credentials and `.env`
- Candidate profile data
- Local SQLite databases and backups
- Python virtual environments
- API tokens and private keys
- Personal resumes and other confidential documents

The application does not automatically submit job applications or authenticate to restricted job portals.

## 12. Development Roadmap

| Milestone | Capability | Status |
|---|---|---|
| Step 1 | Streamlit dashboard and SQLite tracking | Completed |
| Step 2 | Candidate profile management | Completed |
| Step 3 | Keyword-based job matching | Completed |
| Step 4 | CSV discovery and public feed preview | Completed |
| Step 4.1 | PostgreSQL persistence | Completed |
| Step 5.1 | Smart discovery and duplicate classification | Completed |
| Step 5.2 | Controlled import with user approval | Completed |
| Step 5.3 | BFSI relevance ranking | Implemented; automated tests passed |
| Step 5.4 | Enhanced resume-to-job matching | Planned |
| Future | Expanded job-source integrations | Proposed |
| Future | Semantic matching and AI-assisted recommendations | Proposed |
| Future | Notifications and scheduled discovery | Proposed |
| Future | Analytics and deployment | Proposed |

Planned features are not yet implemented.

## 13. Project Objective

The long-term objective is to evolve this application from a local, rules-driven job tracking prototype into an explainable, AI-assisted career opportunity platform.

Potential future capabilities include semantic resume matching, job-description analysis, personalized ranking, expanded integrations, and user-controlled workflow automation.

The project also demonstrates iterative product development, modular architecture, database migration, deterministic decision logic, testing, and human-in-the-loop approval.

---

**Maintainer:** [Manojkmr7992](https://github.com/Manojkmr7992)

**Repository:** [AI-Job-Hunter-India](https://github.com/Manojkmr7992/AI-Job-Hunter-India)

**Current version:** Step 5.3

CI/CD automatic trigger test - November 23, 2026
