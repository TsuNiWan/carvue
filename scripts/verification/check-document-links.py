import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

root = Path(__file__).resolve().parents[2]
checked = []
missing = []
for document in [root / 'README.md', *sorted((root / 'docs').glob('*.md'))]:
    for match in re.finditer(r'\[[^\]\n]+\]\(([^)\n]+)\)', document.read_text(encoding='utf-8-sig')):
        reference = match.group(1).strip('<>')
        if reference.startswith(('https://', 'http://', '#', 'mailto:')):
            continue
        target = (document.parent / unquote(reference.split('#')[0])).resolve()
        entry = {'document': str(document.relative_to(root)), 'reference': reference, 'exists': target.exists()}
        checked.append(entry)
        if not entry['exists']:
            missing.append(entry)
report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'checked': len(checked), 'missing': missing, 'links': checked}
destination = root / 'artifacts/product/delivery-document-links.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'checked': len(checked), 'missing': missing}, ensure_ascii=False))
if missing:
    raise SystemExit(1)
