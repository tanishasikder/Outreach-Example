'''
Makes a trained version live (moves models/latest.json) if it passes the checks:
  1. It beats always guessing the most common status.
  2. It is not worse than the live model on the same test deals (within TOLERANCE).

    python -m src.pipeline.promote 20261019T120000Z           # what Airflow runs
    python -m src.pipeline.promote 20261012T090000Z --force   # roll back to an older version

Exit code 99 means "checked, not promoted": Airflow marks the task skipped, not failed,
and the current live model keeps serving.
'''

import argparse
import sys

from src.core import model_registry

TOLERANCE = 0.01
NOT_PROMOTED = 99

def check(m: dict) -> str | None:
    '''Returns the reason it can't be promoted, or None if it can'''
    if m['accuracy'] <= m['baseline_accuracy']:
        return f"accuracy {m['accuracy']} does not beat always guessing ({m['baseline_accuracy']})"
    live = m.get('live')
    if live and m['macro_f1'] < live['macro_f1'] - TOLERANCE:
        return f"macro F1 {m['macro_f1']} is worse than the live model {live['version']} ({live['macro_f1']})"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('version')
    ap.add_argument('--force', action='store_true', help='skip the checks (for rollbacks)')
    args = ap.parse_args()

    m = model_registry.metrics(args.version)
    if m is None:
        sys.exit(f'Version {args.version} not found')

    if args.force:
        model_registry.promote(args.version, reason='forced')
        print(f'{args.version} is live (forced)')
        return

    problem = check(m)
    if problem:
        print(f'Not promoting {args.version}: {problem}')
        sys.exit(NOT_PROMOTED)

    model_registry.promote(args.version, reason='passed checks')
    print(f"{args.version} is live: accuracy {m['accuracy']}, macro F1 {m['macro_f1']}")

if __name__ == '__main__':
    main()
