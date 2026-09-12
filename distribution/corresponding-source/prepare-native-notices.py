"""Recreate the reviewed supplemental package notices from verified source archives."""
import argparse
import importlib.util
import json
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('source_notices', here/'collect-notices.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((here/'source-manifest.json').read_text())
    inputs = json.loads((here/'native-notice-inputs.json').read_text())
    print(json.dumps(collector.collect(manifest, inputs, args.cache, args.output), indent=2))
