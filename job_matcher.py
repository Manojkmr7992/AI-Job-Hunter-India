"""Explainable offline job-to-profile matching. No external API or database writes."""
from __future__ import annotations
import re
from candidate_profile import choose_resume, validate_profile

ALIASES = {
    'Product ownership': ['product owner', 'product ownership', 'product backlog', 'backlog prioritization'],
    'Product strategy': ['product vision', 'product strategy', 'product roadmap', 'roadmap'],
    'Requirements': ['user stories', 'user story', 'acceptance criteria', 'epics', 'requirements'],
    'Agile delivery': ['safe', 'scrum', 'agile', 'pi planning', 'sprint planning'],
    'Data engineering': ['data engineering', 'etl', 'elt', 'data ingestion', 'data pipeline', 'data migration'],
    'SQL': ['sql', 'sql reconciliation', 'source-to-target'],
    'Data governance': ['data lineage', 'data quality', 'data mapping', 'data validation'],
    'Snowflake': ['snowflake'], 'Teradata': ['teradata'],
    'AWS S3': ['aws', 'amazon web services', 's3'],
    'Informatica': ['informatica'], 'Hadoop': ['hadoop'], 'Hive': ['hive'], 'Spark': ['spark', 'pyspark'],
    'REST API': ['rest api', 'restful', 'api integration', 'rest/soap'],
    'JSON': ['json'], 'Postman': ['postman'], 'OpenAPI': ['swagger', 'openapi'],
    'Kafka': ['kafka'], 'Python': ['python'], 'Databricks': ['databricks'],
    'MySQL': ['mysql'], 'OAuth': ['oauth', 'oauth2'],
    'AI product': ['agentic ai', 'ai product', 'artificial intelligence', 'generative ai'],
    'BFSI': ['banking', 'financial services', 'bfsi', 'bank'],
    'AML': ['aml', 'anti money laundering', 'transaction monitoring'],
    'Credit risk': ['credit risk', 'credit cards', 'lending', 'underwriting'],
    'Payments': ['payments', 'payment processing'],
    'Jira': ['jira'], 'UAT': ['uat', 'user acceptance testing'],
    'ROI': ['roi', 'cost benefit', 'cost-benefit'],
    'CBAP': ['cbap'], 'SAFe POPM': ['popm', 'safe product owner'],
}
# Map consolidated profile skill entries to distinct job requirements.
SKILL_LINKS = {
    'Product ownership':['Product roadmap and backlog ownership'],
    'Product strategy':['Product vision and strategy'],
    'Requirements':['Epics, features, user stories and acceptance criteria'],
    'Agile delivery':['SAFe 6.0, Scrum and PI Planning'],
    'Data engineering':['ETL/ELT and data ingestion workflows'],
    'SQL':['SQL reconciliation and data validation'],
    'Data governance':['Data lineage, mapping and migration','SQL reconciliation and data validation'],
    'Snowflake':['Snowflake'], 'Teradata':['Teradata'], 'AWS S3':['AWS S3'],
    'Informatica':['Informatica, Hadoop, Hive and Spark'],
    'Hadoop':['Informatica, Hadoop, Hive and Spark'], 'Hive':['Informatica, Hadoop, Hive and Spark'],
    'Spark':['Informatica, Hadoop, Hive and Spark'],
    'REST API':['REST APIs, JSON and Postman'], 'JSON':['REST APIs, JSON and Postman'],
    'Postman':['REST APIs, JSON and Postman'], 'OpenAPI':['Swagger/OpenAPI and API mapping'],
    'Kafka':['Kafka-based integration'], 'Python':['Python'],
    'Databricks':['Databricks'], 'MySQL':['MySQL'], 'OAuth':['OAuth'],
    'AI product':['Agentic AI product discovery'],
    'Jira':['Jira, Azure DevOps and Confluence'], 'UAT':['UAT and defect coordination'],
    'ROI':['Cost-benefit, ROI and gap/impact analysis'],
}
DOMAIN_LINKS = {'BFSI':['Banking','Financial Services'], 'AML':['AML Transaction Monitoring'],
                'Credit risk':['Credit Risk','Credit Cards','Lending'], 'Payments':['Payments']}
CERT_LINKS = {'CBAP':'CBAP', 'SAFe POPM':'POPM'}


def _contains(text: str, phrase: str) -> bool:
    return re.search(r'(?<!\w)' + re.escape(phrase.casefold()) + r'(?!\w)', text.casefold()) is not None


def _requirement_evidence(key: str, profile: dict) -> tuple[str, str]:
    if key in DOMAIN_LINKS:
        if any(domain.casefold() == x.casefold() for domain in profile['domains'] for x in DOMAIN_LINKS[key]):
            return 'resume_documented', 'Domain listed in resume-based profile'
        return 'missing', 'Domain not in profile'
    if key in CERT_LINKS:
        if any(CERT_LINKS[key].casefold() in cert.casefold() for cert in profile['certifications']):
            return 'resume_documented', 'Certification listed in profile'
        return 'missing', 'Certification not listed'
    linked = SKILL_LINKS.get(key, [])
    matches = [skill for skill in profile['skills'] if skill['name'] in linked]
    if not matches:
        return 'missing', 'Not documented in profile'
    documented = next((s for s in matches if s['evidence'] == 'resume_documented'), None)
    if documented:
        return 'resume_documented', f"Resume documented; proficiency: {documented['proficiency']}"
    return 'self_reported', 'Self-reported; proficiency not confirmed'


def analyze_job(title: str, description: str, profile: dict) -> dict:
    """Match explicit JD terms only. Scores measure coverage, not hiring probability."""
    if not isinstance(title, str) or not isinstance(description, str):
        raise TypeError('title and description must be strings')
    if not title.strip() or not description.strip():
        raise ValueError('Enter a job title and a nonempty job description')
    validate_profile(profile)
    text = description  # Title selects resume; JD text alone determines skill coverage
    requirements = [key for key, aliases in ALIASES.items() if any(_contains(text, alias) for alias in aliases)]
    evidence = [{'requirement': key, 'status': _requirement_evidence(key, profile)[0],
                 'detail': _requirement_evidence(key, profile)[1]} for key in requirements]
    # Evidence confidence: documented=1, self-reported=0.25, missing=0.
    weights = {'resume_documented': 1.0, 'self_reported': 0.25, 'missing': 0.0}
    score = round(100 * sum(weights[e['status']] for e in evidence) / len(evidence)) if evidence else 0
    resume = choose_resume(title, profile)

    # Local import avoids a circular import with jd_requirements.
    from jd_requirements import extract_requirements

    classifications = {
        item['requirement']: item['classification']
        for item in extract_requirements(description)
    }

    category_weights = {
        'required': 3.0,
        'preferred': 1.0,
        'unspecified': 1.0,
    }

    enhanced_evidence = [
        {
            **item,
            'classification': classifications.get(
                item['requirement'], 'unspecified'
            ),
        }
        for item in evidence
    ]

    total_weight = sum(
        category_weights[item['classification']]
        for item in enhanced_evidence
    )

    weighted_score = (
        round(
            100 * sum(
                category_weights[item['classification']]
                * weights[item['status']]
                for item in enhanced_evidence
            ) / total_weight
        )
        if total_weight else 0
    )

    missing_required = [
        item['requirement']
        for item in enhanced_evidence
        if item['classification'] == 'required'
        and item['status'] == 'missing'
    ]

    return {'job_title': title.strip(), 'recommended_resume': resume,
            'score': score, 'requirements_found': len(requirements),
            'evidence': evidence,
             'enhanced_evidence': enhanced_evidence,
             'weighted_score': weighted_score,
             'missing_required': missing_required,
             'weighted_method': 'Section-weighted keyword coverage',
             'method': 'Offline keyword coverage (not AI semantic analysis)',
            'warning': ('No recognized requirements; score is not meaningful.' if not evidence else
                        'Matching uses recognized JD terms and explicit section headings. Required qualifications outside recognized sections may not be identified. Scores do not establish job eligibility.')}
