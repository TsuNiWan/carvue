"""Combine explicit reruns with the original cases without hiding initial outcomes."""
import json
import sys
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cases = {}
batches = []
for name in sys.argv[1:]:
    folder = (root / 'docs/evidence' / name).resolve()
    assert folder.is_relative_to(root / 'docs/evidence')
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    batches.append({'batch': name, 'stats': summary['stats']})
    for case in json.loads((folder / 'cases.json').read_text(encoding='utf-8')):
        key = (case['projectName'], case['location']['file'], case['title'])
        cases[key] = {**case, 'batch': name}
counts = Counter(case['outcome'] for case in cases.values())
report = {'batches': batches, 'latestOutcomes': dict(counts), 'totalUniqueCases': len(cases),
          'cases': list(cases.values())}
(root / 'docs/evidence/browser-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'total': len(cases), 'latestOutcomes': dict(counts)}))
assert counts['unexpected'] == 0 and counts['flaky'] == 0, 'Unresolved browser cases remain'
