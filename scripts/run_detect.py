"""Show the differences found for every benchmark pair vs the planted causes.

Run from the whydiff folder:  python scripts/run_detect.py
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from whydiff.detectors import diff_profiles  # noqa: E402
from whydiff.profile import UnsupportedConstruct, build_profile  # noqa: E402


def main():
    for d in sorted((ROOT / "benchmark" / "pairs").glob("P*")):
        m = yaml.safe_load((d / "manifest.yaml").read_text())
        try:
            diffs = diff_profiles(build_profile((d / "query_a.sql").read_text()),
                                  build_profile((d / "query_b.sql").read_text()))
        except UnsupportedConstruct as e:
            print(f"{m['id']}  UNSUPPORTED: {e}")
            continue
        got = sorted(x.kind for x in diffs)
        want = sorted(m["planted_causes"])
        print(f"{m['id']}  planted={want}  found={got}  {'OK' if got == want else 'MISMATCH'}")
        for x in diffs:
            print(f"      {x.id} {x.kind}: {x.description}")


if __name__ == "__main__":
    main()