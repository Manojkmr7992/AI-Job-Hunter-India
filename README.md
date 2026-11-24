# AI Job Hunter India

**A Python and Streamlit-based job discovery, filtering, matching, and application tracking platform for BFSI and technical product leadership opportunities in India.**

**Latest source checkpoint:** `2f02efb` — Phase 6, Step 22.4.5.3 (November 23, 2026)  
**Last verified deployment:** Docker image v15 — Jenkins build #15; newer checkpoint deployment pending verification  
**Status:** Operational local deployment; rule-based discovery and matching  
**Technology:** Python 3.11 · Streamlit · PostgreSQL 17 · SQLite · SQLAlchemy · Psycopg · Pytest · Docker · Colima · Jenkins · GitHub

![Python](https://img.shields.io/badge/Python-3.11-blue) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue) ![Tests](https://img.shields.io/badge/local_tests-181_passed-brightgreen) ![Jenkins](https://img.shields.io/badge/Jenkins-build_15_success-brightgreen)

> Badges distinguish the latest locally verified tests from the last verified CI deployment; they are not live CI status.

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

### BFSI Relevance Ranking — Legacy Dashboard (Step 5.3)

- Calculate deterministic relevance scores from available job information.
- Evaluate BFSI, technical/data, seniority, and location signals.
- Assign High match, Good match, Low evidence, or Excluded categories.
- Provide reasons explaining the assigned ranking.

Ranking is advisory. It does not override eligibility or duplicate controls.

**Current limitation:** The existing Streamlit dashboard still displays legacy scoring. The new weighted ranking is integrated into the backend preview; dashboard enhancement is next. Optional CSV descriptions are now retained in discovery, but are not persisted in the database. Both scoring approaches are deterministic, not trained ML models.

### Controlled Job Import

- Allow explicit selection of eligible postings.
- Require user confirmation before importing.
- Revalidate records before saving.
- Persist approved records to the configured database.

### Application Tracking

Track job applications using the following statuses:

`discovered` → `applied` → `interview` → `offer`

Other supported outcomes include `rejected` and `skipped`.

### Phase 6 — Multi-source discovery foundation

- `job_sources.json` and `source_registry.py`: 18 configurable sources, validated registry and lookup helpers. Registered sources are disabled pending integration validation.
- `company_master.json` and `company_master.py`: 122 employers across global and Indian banks, payments, fintech, banking technology, consulting/IT and financial services. Alias resolution and priority metadata support ranking, not a company whitelist.
- `job_taxonomy.json` and `job_classifier.py`: 89 title entries across nine role families, 16 BFSI domains, seniority, skills and location evidence.
- `job_ranker.py`: explainable 100-point relevance scoring, recommendations and per-component breakdowns.
- Expanded eligibility uses whole-phrase title matching and blocks explicit junior/entry-level roles from import. Unknown employers remain supported. Incomplete records remain visible for review.
- `smart_discovery.py` enriches every preview row with classification and ranking while retaining original row identity, normalized fields, optional description and existing eligibility/duplicate decisions.

| Scoring component | Maximum points |
|---|---:|
| Role relevance | 30 |
| BFSI relevance | 25 |
| Seniority | 20 |
| Skills relevance | 15 |
| Location | 5 |
| Employer preference | 5 |
| Total | 100 |

Recommendation bands: Excellent match (85+), Strong match (70+), Potential match (55+), Manual review (40+), Low relevance (below 40). Classification overrides can produce Manual review, Lower priority or Outside target independently of score. Scores are job relevance heuristics, not resume-fit probabilities.

Role families include product ownership, product management, business systems analysis, business analysis, data products, AI products, banking leadership, product strategy and product analysis. BFSI coverage includes retail/commercial banking, cards, payments, AML transaction monitoring, fraud, KYC/sanctions, mortgage/HELOC, lending, credit risk, regulatory compliance, capital markets, wealth, insurance, digital banking and BFSI data/cloud/AI.

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
             CLASSIFICATION & RANKING
          (Taxonomy / Employer / 100 points)
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

Public Greenhouse feed preview is also supported in the discovery module. It does not constitute unrestricted job-board scraping. The new weighted scores are available in backend preview records; the UI still uses the legacy ranking presentation. Future source adapters will feed the same normalization and review pipeline.

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
├── source_registry.py
├── job_sources.json
├── company_master.py
├── company_master.json
├── job_taxonomy.json
├── job_classifier.py
├── job_ranker.py
├── jd_requirements.py
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
├── test_source_registry.py
├── test_company_master.py
├── test_job_classifier.py
├── test_job_ranker.py
│
├── Dockerfile
├── Jenkinsfile
├── .dockerignore
├── jenkins/
│   └── Dockerfile.agent
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

The example above is abbreviated. The current rules file contains the expanded taxonomy titles. Keep rules.json synchronized with job_taxonomy.json when changing target roles. Location eligibility remains strict: preferred cities or confirmed Remote India. Explicit junior/entry-level titles are excluded from import; unknown employers are not excluded solely for being unknown.

## 8. CSV Job Import

The CSV parser requires the following columns:

```csv
url,title,company,location,country,work_mode
```

Example fictional record:

```csv
https://example.com/jobs/demo-001,Technical Product Owner,Demo Bank,Bengaluru,India,Hybrid
```

Supported work modes include Remote, Hybrid, and Onsite. An optional seventh column, `description`, is supported and preserved through normalization and preview for classification. The existing database schema stores the six required fields and status; description and ranking persistence are planned.

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

**Latest local regression result:** 181 tests passed in 1.98 seconds at Step 22.4.5.3 (November 23, 2026). **Last verified CI result:** Jenkins build #15, 105 tests passed in 1.86 seconds. CI verification of the new checkpoint is pending.

| Milestone | Passing tests |
|---|---:|
| PostgreSQL CI/CD baseline | 59 |
| Source registry | 72 |
| Company master | 105 |
| Classification and ranking integration | 181 |

Regression DEF-22.4.5-001: expanded Business Analyst eligibility inadvertently admitted a Junior Business Analyst. Centralized seniority classification corrected the issue without weakening the existing test.

Tests cover core application behavior, candidate profiles, job matching, job discovery, smart discovery, controlled imports, and BFSI filtering.

CI explicitly selects SQLite and unsets DATABASE_URL so regression tests do not write to the deployed PostgreSQL database. Separate read-only PostgreSQL connectivity checks run before and after deployment.

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

## 12. Deployment Architecture and DevOps

The project runs locally on macOS using Colima as the Docker runtime. GitHub hosts source code; Jenkins orchestrates builds and deployments. This is a local deployment, not an AWS-hosted or highly available production service.

```mermaid
flowchart TD
    DEV["VS Code / Python / Git"] --> GH["GitHub main branch"]
    GH -->|"SCM polling or manual build"| JC["Jenkins controller"]
    JC --> JA["Jenkins agent: Python 3.11 + Docker CLI"]
    JA --> TEST["Pytest: isolated SQLite"]
    TEST --> IMG["Versioned Docker image"]
    JC --> SEC["Jenkins Secret File"]
    SEC --> PRE["PostgreSQL preflight"]
    IMG --> PRE
    PRE --> APP["Streamlit container"]
    BROWSER["Local browser :8501"] --> APP
    APP -->|"SQLAlchemy / Psycopg :5432"| PG["PostgreSQL 17"]
    PG --> VOL[("Persistent Docker volume")]
    APP --> HEALTH["HTTP + database verification"]
    HEALTH -->|"Success"| TAG["Publish latest tag"]
    HEALTH -->|"Failure"| RB["Attempt application rollback"]
```

### Infrastructure inventory

| Component | Implementation | Purpose |
|---|---|---|
| Development | VS Code, Python virtual environment | Local development and debugging |
| SQL client | SQLTools / psql | Database inspection and validation |
| Source control | Git / GitHub, main branch | Versioned application and pipeline |
| Container runtime | Docker on Colima | Local isolated services |
| Application image | ai-job-hunter-india:12 | Python 3.11 slim Bookworm, non-root appuser |
| Application container | ai-job-hunter-app | Streamlit runtime |
| Jenkins controller | jenkins/jenkins:lts-jdk21 | Pipeline orchestration |
| Jenkins agent | ai-job-hunter-jenkins-agent:docker | Python, Java and Docker CLI execution |
| Database container | ai-job-hunter-postgres, postgres:17 | Persistent relational storage |
| Application network | ai-job-hunter-network | Internal Docker DNS and database access |
| Jenkins network | jenkins-network | Controller-to-agent communication |
| Database volume | ai-job-hunter-pgdata | Persistent PostgreSQL data |

### Service connections

| Service | Host access | Internal connection |
|---|---|---|
| Streamlit | http://localhost:8501 | Container port 8501 |
| Jenkins | http://localhost:8080 | Controller port 8080 |
| Jenkins agent endpoint | 127.0.0.1:50000 | Controller port 50000; agent uses WebSocket |
| PostgreSQL | 127.0.0.1:5433 | ai-job-hunter-postgres:5432 |

Published ports are bound to loopback in the verified deployment. The Jenkins agent accesses the Docker daemon through its mounted socket; this is privileged access and must be restricted to trusted jobs and users.

### CI/CD pipeline

The declarative Groovy Jenkinsfile uses the python-agent label, disables concurrent builds, timestamps logs, and checks out source from GitHub. Poll SCM was configured with H/5 * * * *; manual builds are also supported. Automatic SCM triggering was verified before the PostgreSQL cutover; build #12 was manually triggered.

| Stage | Responsibility |
|---|---|
| 1. Checkout | Retrieve the selected Git revision |
| 2. Setup Python | Create a clean virtual environment |
| 3. Install Dependencies | Install application and test packages |
| 4. Run Python Tests | Run pytest with SQLite isolation |
| 5. Build Docker Image | Tag image with Jenkins BUILD_NUMBER |
| 6. Validate Deployment Prerequisites | Check network, database and existing application health, profile readability |
| 7. Validate PostgreSQL Connectivity | Inject credentials and query database from new image |
| 8. Deploy and Verify Application | Preserve previous container, deploy, check HTTP health and database access, tag latest |

Post actions report success/failure and clean the workspace. Failed prerequisites prevent replacement of the existing application. Failed deployment triggers a best-effort application rollback; database changes are not automatically rolled back. Deployment replaces the container and is not zero-downtime.

### Docker image and security

- Base image: python:3.11-slim-bookworm.
- Application runs as non-root appuser (UID 10001).
- Streamlit health check uses /_stcore/health.
- Candidate profile is mounted read-only from a private host file.
- .dockerignore excludes private profiles, credentials, databases, virtual environments and test artifacts.
- Versioned images support release traceability; latest is assigned after successful validation.

## 13. PostgreSQL Architecture and Cutover

The persistence layer selects SQLite or PostgreSQL using JOB_HUNTER_DB. PostgreSQL uses SQLAlchemy and Psycopg, with connection pool pre-ping. The deployed application uses PostgreSQL; SQLite remains available for local development and regression testing.

| Database property | Value |
|---|---|
| Engine | PostgreSQL 17 |
| Database | ai_job_hunter |
| Schema | public |
| Table | jobs |
| Application role | job_hunter_user |
| Host port | 5433 |
| Container port | 5432 |
| Persistent volume | ai-job-hunter-pgdata |

The application role is not a superuser and has database CONNECT and schema USAGE/CREATE privileges for application-owned objects.

### Current logical data model

| Column | Type / constraint |
|---|---|
| id | Integer identity primary key |
| url | Text, unique, not null |
| title | Text, not null |
| company | Text, not null |
| location | Text, not null |
| country | Text, not null |
| work_mode | Text, not null |
| status | Text, not null, default discovered |

URL-based upsert prevents duplicate URLs and updates job attributes without resetting existing application status. The persistence layer supports initialization, insert/upsert, listing and status updates.

### Migration and validation history

- Provisioned PostgreSQL container, private network and persistent volume.
- Created a restricted application role and initialized the jobs table.
- Verified local Python and container-to-database connectivity.
- Reconciled SQLite and PostgreSQL: both initially contained zero jobs; no record transfer was necessary.
- Validated application persistence operations with temporary test records and cleanup.
- Suspended Jenkins during cutover; created a SQLite backup and preserved the original container.
- Deployed the existing image with PostgreSQL configuration, verified health and database connectivity.
- Updated Jenkinsfile, configured Secret File credentials and successfully deployed image v12.

### Credential management

Store actual environment files outside the repository, for example under ~/.config/ai-job-hunter/ with restrictive permissions (600). Use different database hosts for local Python and container execution.

Example container configuration (placeholders only):

```dotenv
JOB_HUNTER_DB=postgres
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_URL_ENCODED_PASSWORD@ai-job-hunter-postgres:5432/ai_job_hunter
```

For local Python connecting to the container, use 127.0.0.1:5433 instead.

Jenkins uses a Secret File credential with ID ai-job-hunter-postgres-env, bound temporarily through withCredentials and passed to Docker using --env-file. Shell tracing is disabled around secret handling. Docker administrators can still inspect container environment variables; do not grant untrusted users Docker access.

## 14. Operational Runbook

These commands assume the local infrastructure has already been provisioned. Fresh installations must create the database, role, Docker network, volume, private profile and Jenkins controller/agent configuration first. The Jenkinsfile profile bind path is machine-specific and must be adapted for other hosts.

```bash
# Start the local Docker runtime if stopped
colima start

# Inspect running services
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

# Build a local application image
docker build -t ai-job-hunter-india:local .

# Check deployed application
docker inspect ai-job-hunter-app --format 'Image={{.Config.Image}} Health={{.State.Health.Status}} Network={{.HostConfig.NetworkMode}}'
curl --fail http://localhost:8501/_stcore/health

# Verify database using the local container
docker exec ai-job-hunter-postgres psql -U job_hunter_user -d ai_job_hunter -P pager=off -c "SELECT current_database(), current_user, COUNT(*) AS total_jobs FROM public.jobs;"

# Inspect application logs
docker logs --tail 50 ai-job-hunter-app

# Inspect rollback containers
docker ps -a --filter name=ai-job-hunter-app
```

### Release workflow

Review changes locally, run pytest, commit intended files and push to GitHub. Jenkins polls for SCM changes or can be triggered manually through the dashboard. Review console output and confirm the deployed image, HTTP health and database connectivity.

### Troubleshooting

| Symptom | Action |
|---|---|
| Docker unavailable | Check Colima and Docker daemon status |
| Jenkins agent offline | Inspect agent logs and controller connectivity |
| Missing credential ID | Create the matching Jenkins Secret File credential |
| PostgreSQL connection failure | Check network, hostname, port, role and protected environment file |
| Unhealthy application | Review container logs and rollback status |
| Legacy Docker builder warning | Plan a BuildKit/buildx upgrade; warning did not block build #12 |

Retain the legacy SQLite backup and version-specific rollback containers until a controlled retention policy is established. Back up PostgreSQL independently; a persistent volume is not a backup.

## 15. Verified Release Evidence

The following table preserves historical build #12 evidence. Subsequent verified builds #13, #14 and #15 succeeded; build #15 deployed `ai-job-hunter-india:15` from revision `884dc53`, with 105 passing tests, healthy application and PostgreSQL connectivity. The new source checkpoint has 181 local passing tests; its deployment is not yet verified.

| Metric | Last verified result |
|---|---|
| Jenkins build | #12 — SUCCESS |
| Application source revision | db448fb |
| Regression tests | 59 passed |
| Pipeline stages | 8 of 8 passed |
| Approximate logged execution window | 44 seconds |
| Deployed image | ai-job-hunter-india:12 |
| Application health | healthy |
| PostgreSQL health | healthy |
| Database connection | ai_job_hunter / job_hunter_user |
| Job records at validation | 0 |
| HTTP health response | ok |
| Previous application | ai-job-hunter-app-rollback-12 |
| Legacy SQLite container | ai-job-hunter-app-sqlite-backup |

Build #11 failed safely because the Jenkins credential was missing. After adding the credential, build #12 completed successfully without further application code changes. Rollback is implemented but a forced deployment-failure recovery test has not been documented.

## 16. Development Roadmap

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
| Infrastructure | Docker, Colima, Jenkins CI/CD | Completed |
| Infrastructure | Live PostgreSQL cutover and secure deployment | Completed |
| Step 5.4 | Enhanced resume-to-job matching | Planned |
| 22.2 | Multi-source registry | Completed |
| 22.3 | Company master | Completed |
| 22.4.1–22.4.4 | Taxonomy, classification, ranking and unit tests | Completed |
| 22.4.5.1–22.4.5.3 | Integration assessment, eligibility, descriptions and backend ranking | Completed |
| 22.4.5.4 | Streamlit weighted ranking dashboard | Next |
| 22.4.5.5 | End-to-end integration tests | Pending |
| 22.4.6–22.4.7 | Final integration commit and CI/CD verification | Pending |
| 22.5–22.6 | Live public API validation and Greenhouse/Lever/Ashby ingestion | Planned |
| 22.7–22.10 | Gmail API, portal alerts, recruiter emails and attachments | Planned |
| 22.11–22.12 | Permitted company career feeds and authorized search API | Planned |
| 22.13 onward | Database enhancements, scheduling and monitoring | Planned |
| Future | Semantic matching and AI-assisted recommendations | Proposed |
| Future | Notifications and scheduled discovery | Proposed |
| Future | Layered data ingestion and ETL orchestration | Proposed |
| Future | LLMs, embeddings, RAG and vector search | Proposed |
| Future | Agentic AI with human approval | Proposed |
| Future | Analytics, observability and AWS deployment | Proposed |

Planned features are not yet implemented.

### Live source strategy

Registered sources include Naukri, LinkedIn, Indeed, Foundit, iimjobs, Hirist, Instahyre, Cutshort, recruiter email, email attachments, Greenhouse, Lever, Ashby, Workday, company careers, Adzuna, manual CSV and manual JD. Portal alerts will use authorized Gmail access; public ATS endpoints and employer feeds require source-specific validation. Public visibility does not imply permission for automated scraping. No login bypass or automatic applications are planned. Gmail OAuth credentials and tokens must remain outside source control and logs. The existing Greenhouse preview is basic; automated multi-source retrieval is not yet operational. Synthetic test URLs are fixtures, not live job results.

## 17. Project Objective

The long-term objective is to evolve this application from a local, rules-driven job tracking prototype into an explainable, AI-assisted career opportunity platform.

Potential future capabilities include semantic resume matching, job-description analysis, personalized ranking, expanded integrations, and user-controlled workflow automation.

The project also demonstrates iterative product development, modular architecture, database migration, deterministic decision logic, testing, and human-in-the-loop approval.

---

**Maintainer:** [Manojkmr7992](https://github.com/Manojkmr7992)

**Repository:** [AI-Job-Hunter-India](https://github.com/Manojkmr7992/AI-Job-Hunter-India)

**Last verified deployment:** v15 — November 23, 2026 (Eastern Time)  
**Latest locally validated source:** `2f02efb` — 181 passing tests.  
**Resume development at:** Step 22.4.5.4 — Streamlit weighted ranking dashboard.

This project demonstrates hands-on technical product ownership across requirements, architecture, implementation, data persistence, acceptance testing, release management and operational validation. It is a personal portfolio project; planned AI capabilities are not represented as implemented.

## Phase 6 - Live Job Discovery

### Implemented capabilities

- Greenhouse, Lever and Ashby public API connectors.
- 18 configured employer boards, 10 verified and enabled.
- 122-employer master directory.
- 115 target job titles across 9 role families.
- 16 BFSI domain classifications.
- Role-first and seniority screening.
- Location and work-mode normalization.
- Weighted ranking and classification evidence.
- Suppressed job records audit.
- User-approved controlled imports.
- Duplicate prevention and post-import re-ranking.
- SSL certificate verification using certifi.

### Local validation - November 24, 2026

- Existing application tests: 181
- Screening regression tests: 12
- Connector and normalization tests: 37
- Controlled import integration tests: 6
- Total automated tests: 236 passed
- Dependency consistency: Passed

### Live screening validation

- India candidates: 183
- Unrelated roles suppressed: 181
- Junior roles suppressed: 0
- Retained for ranking: 2
- Screening reconciliation: Passed

### Known limitations

- Current employer sources have limited product-role coverage.
- Missing work-mode information requires manual review.
- Full screening recall has not been established.
- Controlled import integration tests use simulated persistence.
- Deployment validation remains pending.

### Next implementation priorities

1. Google Cloud and Gmail API integration.
2. Naukri job alert ingestion.
3. LinkedIn job alert ingestion.
4. Banking and consulting employer career integrations.
5. Recruiter email and job description extraction.
