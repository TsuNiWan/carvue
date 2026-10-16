import base64
import io
import json
from pathlib import Path
import re
import sys
import zipfile


batch = Path(sys.argv[1]).resolve()
root = Path('artifacts/product').resolve()
assert batch.is_relative_to(root)
html_path = batch / 'report/index.html'
if not html_path.exists():
    html_path = batch / 'index.html'
html = html_path.read_text(encoding='utf-8')
match = re.search(r'<template id="playwrightReportBase64">data:application/zip;base64,([^<]+)</template>', html)
assert match, 'Missing embedded report data'
attachments = batch / 'attachments'
attachments.mkdir(exist_ok=True)
data = batch / 'report-data'
data.mkdir(exist_ok=True)
counts = {}


def visit(value):
    if isinstance(value, list):
        for child in value:
            visit(child)
    elif isinstance(value, dict):
        if value.get('contentType') == 'application/json' and isinstance(value.get('body'), str):
            name = Path(value['name']).name
            counts[name] = counts.get(name, 0) + 1
            filename = name if counts[name] == 1 else f'{counts[name]}-{name}'
            (attachments / filename).write_text(value['body'], encoding='utf-8')
        for child in value.values():
            visit(child)


with zipfile.ZipFile(io.BytesIO(base64.b64decode(match.group(1)))) as archive:
    for name in archive.namelist():
        if not name.endswith('.json'):
            continue
        document = json.loads(archive.read(name))
        (data / Path(name).name).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
        visit(document)
        if name == 'report.json':
            print(json.dumps({key: document[key] for key in ['stats', 'duration', 'projectNames'] if key in document}, ensure_ascii=False))
print(json.dumps({'batch': str(batch), 'jsonAttachments': sum(counts.values())}))
