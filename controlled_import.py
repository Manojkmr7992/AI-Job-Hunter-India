"""Step 5.2: human-approved, conservative import into the configured job store."""
from __future__ import annotations
from core import add_job, list_jobs
from smart_discovery import preview_jobs, canonical_url, fingerprint


def import_approved(incoming: list[dict], approved_rows: list[int], rules: dict,
                    *, existing: list[dict] | None = None, save=None) -> dict:
    """Only import explicitly selected eligible rows; recheck against stored jobs.

    existing/save are injectable for tests. A URL or semantic collision is never
    automatically overwritten. For concurrent writers, the database URL uniqueness
    constraint remains the final safeguard, but cross-URL concurrent semantic
    duplicates require database-side locking to prevent entirely.
    """
    if len(incoming) > 1000:
        raise ValueError('Maximum 1000 rows per import')
    if any(type(n) is not int or n < 1 or n > len(incoming) for n in approved_rows):
        raise ValueError('Approved row number out of range')
    if len(set(approved_rows)) != len(approved_rows):
        raise ValueError('Duplicate row selections')
    current = list_jobs() if existing is None else list(existing)
    persist = add_job if save is None else save
    report = {'imported': 0, 'skipped_unselected': len(incoming) - len(approved_rows),
              'duplicate_url': 0, 'possible_duplicate': 0, 'excluded': 0,
              'review': 0, 'errors': [], 'imported_rows': []}
    for number in sorted(approved_rows):
        job = incoming[number - 1]
        # Fresh read prevents stale preview from overwriting a job imported in
        # another browser session between preview and confirmation.
        if existing is None:
            current = list_jobs()
        result = preview_jobs([job], current, rules)[0]
        decision = result['decision']
        if decision != 'Eligible':
            field = {'Duplicate URL': 'duplicate_url', 'Possible duplicate': 'possible_duplicate',
                     'Excluded': 'excluded', 'Review': 'review'}[decision]
            report[field] += 1
            continue
        clean = {k: result[k] for k in ('url', 'title', 'company', 'location', 'country', 'work_mode')}
        try:
            persist(clean)
        except Exception as exc:
            report['errors'].append(f'Row {number}: {type(exc).__name__}: {exc}')
            continue
        report['imported'] += 1
        report['imported_rows'].append(number)
        current.append(clean)
    return report
