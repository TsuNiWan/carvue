"""Collect compact, path-sanitized measurements from extracted browser reports."""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
batch = (root / sys.argv[1]).resolve()
assert batch.is_relative_to(root / 'artifacts/product')
destination = root / 'docs/evidence' / batch.name
destination.mkdir(parents=True, exist_ok=True)


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        value = value.replace(str(root), '<workspace>').replace(root.as_posix(), '<workspace>')
        return re.sub(r'[A-Za-z]:[\\/]Users[\\/][^\s"<>]+', '<local-path>', value)
    return value


measurement_count = 0
for source in (batch / 'attachments').glob('*.json'):
    # Wall-clock attachments already contain the individual mechanism samples.
    if source.name.endswith('-samples.json'):
        continue
    document = json.loads(source.read_text(encoding='utf-8'))
    (destination / source.name).write_text(json.dumps(sanitize(document), ensure_ascii=False, indent=2), encoding='utf-8')
    measurement_count += 1
report = json.loads((batch / 'report-data/report.json').read_text(encoding='utf-8'))
cases = [
    {key: test[key] for key in ['testId', 'title', 'projectName', 'location', 'duration', 'outcome', 'ok']}
    for file in report['files'] for test in file['tests']
]
(destination / 'cases.json').write_text(json.dumps(sanitize(cases), ensure_ascii=False, indent=2), encoding='utf-8')
summary = {key: report[key] for key in ['stats', 'duration', 'projectNames'] if key in report}
summary['jsonMeasurements'] = measurement_count
(destination / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
