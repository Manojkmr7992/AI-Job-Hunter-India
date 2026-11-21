from bfsi_filter import assess_job

RULES = {'target_titles': ['Technical Product Owner', 'Data Product Manager'],
         'cities': ['Bengaluru', 'Hyderabad', 'Pune'], 'country': 'India',
         'allow_remote_india': True}


def job(**kwargs):
    data = {'title': 'Technical Product Owner', 'company': 'Example',
            'location': 'Bengaluru', 'country': 'India', 'work_mode': 'Hybrid'}
    data.update(kwargs)
    return data


def test_bfsi_ranked_above_generic():
    a = assess_job(job(company='Bank Payments'), RULES)
    b = assess_job(job(company='Generic Retail'), RULES)
    assert a['score'] > b['score']
    assert a['eligible'] and b['eligible']


def test_technical_signals_increase_score():
    a = assess_job(job(description='AWS Snowflake data platform'), RULES)
    b = assess_job(job(), RULES)
    assert a['score'] > b['score']


def test_junior_title_penalty():
    a = assess_job(job(title='Junior Technical Product Owner'), RULES)
    b = assess_job(job(), RULES)
    assert a['score'] < b['score']


def test_location_exclusion_cannot_be_overridden():
    a = assess_job(job(location='Mumbai', company='Bank AML Payments',
                       description='AWS data cloud platform'), RULES)
    assert not a['eligible'] and a['match_tier'] == 'Excluded'


def test_remote_india_allowed():
    a = assess_job(job(location='Jaipur', work_mode='Remote'), RULES)
    assert a['eligible']


def test_missing_description_does_not_exclude():
    a = assess_job(job(), RULES)
    assert a['eligible'] and any('not established' in x for x in a['reasons'])


def test_score_bounded():
    a = assess_job(job(company='Bank Payments AML Fraud Credit Card Insurance',
                       description='data analytics cloud aws snowflake etl platform ai ml api'), RULES)
    assert 0 <= a['score'] <= 100


def test_explanation_available():
    a = assess_job(job(company='Fintech'), RULES)
    assert a['eligibility_reason'] and a['reasons']
