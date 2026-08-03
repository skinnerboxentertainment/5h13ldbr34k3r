#!/usr/bin/env python3
"""Build the private-mapping fixtures the test suite uses as its hardest case.

Recreates the exact scenario an attacker never sees the dictionary for:

  1. reseed_mapping.py --seed <S>          -> a PRIVATE {src:tgt} mapping
  2. generate_font.py --base-path <base>   -> a brand-new ShieldFont built
     --mapping-path <private>                 from that mapping

The result is a font whose word pairs are unique to this seed. Recovery must
still find every pair with 0 misses (prototype/tests/run_tests.py check 6).

Usage:
  python prototype/tests/build_private_font.py            # uses Arial (Windows)
  python prototype/tests/build_private_font.py --seed 20260803

Outputs:
  tools/private-mapping.json
  shieldfont/public/fonts/shieldfont-private.{ttf,woff2,css}
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REPO = ROOT / "shieldfont"
SEED = "20260803"
BASE_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default=SEED)
    ap.add_argument("--base-path", type=Path)
    ap.add_argument("--pairs", default=str(
        REPO / "benchmark/data/v7/pairs_v7_alpha_v15_0_1_0_0_0_0.json"))
    args = ap.parse_args()

    base = args.base_path or next((p for p in BASE_FONT_CANDIDATES if p.exists()), None)
    if base is None:
        print("no base font found; pass --base-path to a .ttf")
        return 1

    mapping_out = ROOT / "tools" / "private-mapping.json"
    mapping_out.parent.mkdir(exist_ok=True)
    print(f"[build] reseeding mapping with seed {args.seed}")
    subprocess.run([sys.executable, str(REPO / "scripts" / "reseed_mapping.py"),
                    "--seed", args.seed, "--pairs", args.pairs, "--out", str(mapping_out)],
                   check=True, cwd=str(REPO))

    print(f"[build] generating font from {base} with the private mapping")
    subprocess.run([sys.executable, str(REPO / "scripts" / "generate_font.py"),
                    "--base-path", str(base),
                    "--name", "ShieldFont Private",
                    "--prefix", "shieldfont-private",
                    "--mapping-path", str(mapping_out),
                    "--no-mapping-emit"],
                   check=True, cwd=str(REPO))

    print("[build] done: shieldfont/public/fonts/shieldfont-private.ttf "
          "+ tools/private-mapping.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
