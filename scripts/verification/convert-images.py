"""Encode actual rendered PNGs as WebP without changing their content."""
from pathlib import Path
from PIL import Image
import hashlib
import json

root = Path(__file__).resolve().parents[2]
for source in (root / 'assets/source').glob('*/qa/preview.png'):
    Image.open(source).save(root / 'public/previews' / (source.parent.parent.name + '.webp'), quality=92)
for source in (root / 'docs/images').glob('*.png'):
    Image.open(source).save(source.with_suffix('.webp'), quality=92)
record_path = root / 'docs/evidence/readme-capture.json'
if record_path.exists():
    record = json.loads(record_path.read_text(encoding='utf-8'))
    for item in record['records']:
        image_path = root / 'docs/images' / (item['name'] + '.webp')
        data = image_path.read_bytes()
        item['webp'] = {'path': image_path.relative_to(root).as_posix(), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()}
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
