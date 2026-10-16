"""Use the project's existing Three.js dependency for verified convex hull planes."""
import json
import os
import shutil
import subprocess
from pathlib import Path


def convex_support(points):
    node = shutil.which('node')
    if node is None and os.name == 'nt':
        candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'nodejs/node.exe'
        if candidate.is_file():
            node = str(candidate)
    if node is None:
        raise RuntimeError('Node.js is required to build vehicle aperture hulls')
    script = Path(__file__).with_name('convex-hull.mjs')
    result = subprocess.run([node, str(script)], input=json.dumps(points), text=True,
                            capture_output=True, check=True)
    return json.loads(result.stdout)
