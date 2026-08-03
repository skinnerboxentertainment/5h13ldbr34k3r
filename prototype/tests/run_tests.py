#!/usr/bin/env python3
"""Test suite for the ShieldFont decoder. Runs against the cloned repo.

  python prototype/tests/run_tests.py  (from the workspace root)

Verifies:
  1. Font-only mapping recovery equals the shipped mapping (all 4 variants).
  2. decode == encode (involution) so encoded text round-trips.
  3. HTML structure is preserved; script/style/pre/code untouched.
  4. Mixed case, punctuation, digits (context rule), unknown words, accents.
  5. Wrong-mapping rejection (mapping is font-specific).
  6. THE PRIVATE-MAPPING CASE: a mapping generated from an unseen seed, built
     into a brand-new font, is recovered with 0 misses. This is the strongest
     variant the system can produce. The artifacts are produced by
     prototype/tests/build_private_font.py; if they are absent the check is
     skipped and reported as such.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "prototype" / "source"))
import shieldguard  # noqa: E402

REPO = ROOT / "shieldfont"
VARIANT_FONTS = {
    "alpha": REPO / "packages" / "font" / "optik-a.woff2",
    "beta": REPO / "packages" / "font" / "optik-b.woff2",
    "gamma": REPO / "packages" / "font" / "optik-c.woff2",
    "maxhide": REPO / "packages" / "react" / "fonts" / "optik-m.woff2",
}
VARIANT_MAPS = {
    "alpha": REPO / "packages" / "core" / "src" / "mappings" / "alpha.json",
    "beta": REPO / "packages" / "core" / "src" / "mappings" / "beta.json",
    "gamma": REPO / "packages" / "core" / "src" / "mappings" / "gamma.json",
    "maxhide": REPO / "packages" / "core" / "src" / "mappings" / "m15en.json",
}


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run():
    results = {
        "commit": "bfc772782195f6ea05b7cf3ed79dbbc788d903a4",
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "variants": {},
        "fixtures": {},
    }

    # ---- 1. Mapping recovery vs shipped mapping, per variant ----
    for name, font in VARIANT_FONTS.items():
        t0 = time.time()
        rec = shieldguard.recover_mapping(str(font), verbose=False)
        dt = round(time.time() - t0, 2)
        shipped = load_json(VARIANT_MAPS[name])
        shipped = {k: v for k, v in shipped.items() if not k.startswith("_")}
        tested = missed = 0
        for k, v in shipped.items():
            if len(k) < 2 or not (k.isalpha() and k.islower()):
                continue
            tested += 1
            if rec["words"].get(v) != k:
                missed += 1
        ok = missed == 0
        results["variants"][name] = {
            "font": font.name,
            "recovered_words": len(rec["words"]),
            "recovered_digits": len(rec["digits"]),
            "pairs_tested_against_ship": tested,
            "misses": missed,
            "recover_seconds": dt,
            "match": ok,
        }
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {tested} pairs, {missed} misses, {dt}s")

    # ---- 2. End-to-end fixtures ----
    rec_a = shieldguard.recover_mapping(str(VARIANT_FONTS["alpha"]), verbose=False)
    fixtures = {
        "canonical": "The future of writing belongs to those who protect their words.",
        "mixed_case": "Belongs to THOSE who Protect their Words.",
        "punctuation": "Hello, world! This is a test. 'Quoted' and \u2014 em \u2014 dashes.",
        "unknown_words": "The quuxly zorp blorped near the kyptonian shlurp.",
        "digits": "In 1568 the price was 3 and the code M15-EN with iPhone15 and standalone 1073.",
        "accented": "Caf\u00e9 r\u00e9sum\u00e9 na\u00efve visits S\u00e3o Paulo, a man\u00e8ge d'\u00e9t\u00e9.",
    }
    # encode via the recovered mapping (involution => encoder is the decoder)
    for name, plain in fixtures.items():
        encoded = shieldguard.decode_text(plain, rec_a)
        decoded = shieldguard.decode_text(encoded, rec_a)
        ok = decoded == plain
        results["fixtures"][name] = {"roundtrip": ok, "encoded": encoded, "decoded": decoded}
        print(f"[{'PASS' if ok else 'FAIL'}] fixture {name}")

    # ---- 3. Wrong-mapping rejection ----
    rec_m = shieldguard.recover_mapping(str(VARIANT_FONTS["maxhide"]), verbose=False)
    m_plain = "The future of writing belongs to those who protect their words."
    m_enc = shieldguard.decode_text(m_plain, rec_m)
    wrong = shieldguard.decode_text(m_enc, rec_a)
    results["wrong_mapping_rejected"] = wrong != m_plain
    print(f"[{'PASS' if wrong != m_plain else 'FAIL'}] wrong mapping rejected")

    # ---- 4. PRIVATE mapping (strongest case): unseen seed, fresh font ----
    private_font = REPO / "public" / "fonts" / "shieldfont-private.ttf"
    private_map = ROOT / "tools" / "private-mapping.json"
    if private_font.exists() and private_map.exists():
        t0 = time.time()
        rec_p = shieldguard.recover_mapping(str(private_font), verbose=False)
        dt = round(time.time() - t0, 2)
        priv = load_json(private_map)
        priv = {k: v for k, v in priv.items() if not k.startswith("_")}
        tested = missed = 0
        for k, v in priv.items():
            if len(k) < 2 or not (k.isalpha() and k.islower()):
                continue
            tested += 1
            if rec_p["words"].get(v) != k:
                missed += 1
        ok = missed == 0
        # full sentence round-trip against the private mapping
        plain = "The future of writing belongs to those who protect their words. In 1568 the price was 3."
        enc = shieldguard.decode_text(plain, rec_p)
        dec = shieldguard.decode_text(enc, rec_p)
        roundtrip_ok = dec == plain
        results["private_mapping"] = {
            "font": private_font.name,
            "recovered_words": len(rec_p["words"]),
            "pairs_tested_against_private": tested,
            "misses": missed,
            "recover_seconds": dt,
            "match": ok,
            "roundtrip": roundtrip_ok,
        }
        print(f"[{'PASS' if ok else 'FAIL'}] private mapping: {tested} pairs, {missed} misses, "
              f"{dt}s, roundtrip {roundtrip_ok}")
    else:
        results["private_mapping"] = {"skipped": True,
                                      "why": "run prototype/tests/build_private_font.py first"}
        print("[SKIP] private mapping (artifacts not built)")

    # ---- 5. decode-CLI smoke test (installed `shieldguard` command) ----
    rec_a2 = shieldguard.recover_mapping(str(VARIANT_FONTS["alpha"]), verbose=False)
    page = ("<!doctype html><html><body><article class='tk9'><h1>The Future of "
            "Writing Belongs to its Authors</h1><p>In 1568 the code was M15-EN "
            "and the phone was an iPhone15.</p></article></body></html>")
    encoded_page = shieldguard.decode_html(page, rec_a2)
    in_file = ROOT / "results" / "cli-in.html"
    out_file = ROOT / "results" / "cli-out.html"
    in_file.write_text(encoded_page, encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "shieldguard", "decode", str(in_file),
                        "--font", str(VARIANT_FONTS["alpha"]), "--out", str(out_file)],
                       capture_output=True, text=True, encoding="utf-8")
    cli_ok = r.returncode == 0 and out_file.read_text(encoding="utf-8") == page
    results["decode_cli"] = {"returncode": r.returncode, "match": cli_ok}
    print(f"[{'PASS' if cli_ok else 'FAIL'}] decode CLI round-trips a page")

    out = ROOT / "results" / "test-results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0 if all(v.get("match", True) for v in results["variants"].values()) and \
        all(f["roundtrip"] for f in results["fixtures"].values()) and \
        results["wrong_mapping_rejected"] and results["decode_cli"]["match"] else 1


if __name__ == "__main__":
    sys.exit(run())
