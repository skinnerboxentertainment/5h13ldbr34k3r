#!/usr/bin/env python3
"""
shieldguard - font-derived ShieldFont decoder.

Recovers the ShieldFont substitution mapping purely from a built font
(GSUB + glyf + cmap), then decodes protected HTML by applying the inverse
transformation. No repository source required for the mapping.

Usage:
  python shieldguard.py decode input.html --font path/to/font.woff2 --out decoded.html
  python shieldguard.py recover path/to/font.woff2 --json mapping.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import regex
from fontTools.ttLib import TTFont


# ---------------------------------------------------------------------------
# Phase A: recover the word/substitution mapping from a built font alone.
# ---------------------------------------------------------------------------

def _user_cache_dir() -> Path:
    """A per-user cache dir, so an installed package never writes into its own
    source tree. Prefers the platform cache location, falls back to ~/.cache."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "shieldguard"
    return Path.home() / ".cache" / "shieldguard"


_CACHE_DIR = _user_cache_dir()


def _ensure_ttf_cache(font_path: str) -> str:
    """WOFF2 glyf reconstruction is ~100x slower than TTF. Convert once to a
    cached .ttf beside this script and parse that instead."""
    p = Path(font_path)
    if p.suffix.lower() != ".woff2":
        return font_path
    _CACHE_DIR.mkdir(exist_ok=True)
    ttf = _CACHE_DIR / f"{p.stem}.ttf"
    if not ttf.exists():
        f = TTFont(str(p))
        f.flavor = None
        f.save(str(ttf))
        print(f"[cache] converted {p.name} -> {ttf.name}")
    return str(ttf)


def _unwrap_subtable(st):
    """Extension lookups (type 7) wrap the real subtable in ExtSubTable."""
    while getattr(st, "ExtensionLookupType", None) is not None:
        st = st.ExtSubTable
    return st


def _collect_ligatures(lookup):
    """Yield (input_glyph_names, output_glyph_name) for a LigatureSubst lookup."""
    results = []
    for st in lookup.SubTable:
        st = _unwrap_subtable(st)
        for first, ligs in getattr(st, "ligatures", {}).items():
            for lig in ligs:
                input_names = [first] + list(lig.Component)
                results.append((input_names, lig.LigGlyph))
    return results


def _collect_singles(lookup):
    """Yield (from_glyph, to_glyph) for a SingleSubst lookup."""
    results = []
    for st in lookup.SubTable:
        st = _unwrap_subtable(st)
        if hasattr(st, "mapping"):
            for gname, repl in st.mapping.items():
                results.append((gname, repl))
    return results


def recover_mapping(font_path: str, verbose: bool = True) -> dict:
    """Recover {decoy_word: original_word} pairs and digit swaps from a font."""
    font_path = _ensure_ttf_cache(font_path)
    font = TTFont(font_path, lazy=True)
    cmap = font.getBestCmap()
    rev_cmap = {}
    for cp, gname in cmap.items():
        rev_cmap.setdefault(gname, []).append(chr(cp))
    glyf = font["glyf"]
    glyf_is_lazy = bool(getattr(glyf, "glyphs", None) is None or getattr(font, "lazy", False))

    def glyphs_to_text(glyph_names):
        chars = []
        for gn in glyph_names:
            cs = rev_cmap.get(gn)
            if not cs:
                return None
            chars.append(cs[0])
        return "".join(chars)

    # Collect ligature outputs first, then only decompile those composites.
    lig_outputs = set()
    lig_records = []  # (input_names, out_glyph)
    single_records = []
    for lookup in font["GSUB"].table.LookupList.Lookup:
        # Extension lookups (type 7) wrap one real lookup of any base type.
        if lookup.LookupType == 7:
            base_type = _unwrap_subtable(lookup.SubTable[0]).LookupType
        else:
            base_type = lookup.LookupType
        if base_type in (4, 7):
            base = _unwrap_subtable(lookup.SubTable[0])
            if base.LookupType == 4:
                for input_names, out_glyph in _collect_ligatures(lookup):
                    lig_records.append((input_names, out_glyph))
                    lig_outputs.add(out_glyph)
        elif base_type == 1:
            for gname, repl in _collect_singles(lookup):
                single_records.append((gname, repl))

    composites = {}
    for gname in lig_outputs:
        g = glyf[gname]
        if g.isComposite():
            composites[gname] = [c.glyphName for c in g.components]

    word_map = {}   # decoy -> original
    digit_map = {}  # encoded digit -> original digit
    for input_names, out_glyph in lig_records:
        decoy = glyphs_to_text(input_names)
        original = glyphs_to_text(composites.get(out_glyph, []))
        if decoy and original:
            word_map[decoy] = original
    for gname, repl in single_records:
        src = glyphs_to_text([gname])
        tgt = glyphs_to_text([repl])
        if src and tgt:
            digit_map[tgt] = src  # font maps original->encoded; invert

    if verbose:
        print(f"[recover] {len(word_map)} ligature pairs, {len(digit_map)} single-char swaps "
              f"recovered from {Path(font_path).name}")
        shown = 0
        for decoy, original in sorted(word_map.items()):
            if len(decoy) >= 4 and decoy.isalpha() and decoy.islower():
                print(f"  {decoy!r:24} -> {original!r}")
                shown += 1
                if shown >= 8:
                    break

    return {"words": word_map, "digits": digit_map}


# ---------------------------------------------------------------------------
# Phase B: apply the inverse transformation to HTML, preserving structure.
# ---------------------------------------------------------------------------

WORD_RE = regex.compile(r"\p{L}+")
IS_DIGIT = regex.compile(r"^\d$")
IS_LETTER = regex.compile(r"\p{L}")
ENTITY_RE = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[a-zA-Z][a-zA-Z0-9]{1,31});")
SKIP_TAGS = {"script", "style", "code", "pre", "textarea", "svg", "math",
             "noscript", "title", "option"}
RAW_TEXT_TAGS = {"script", "style", "textarea", "title"}
TOKEN_RE = re.compile(r"<!--[\s\S]*?-->|<([!/]?[a-zA-Z](?:[^>\"']|\"[^\"]*\"|'[^']*')*)>")


def entity_spans(s):
    spans = []
    for m in ENTITY_RE.finditer(s):
        spans.append((m.start(), m.end()))
    return spans


def in_entity(spans, i):
    lo, hi = 0, len(spans) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b = spans[mid]
        if i < a:
            hi = mid - 1
        elif i >= b:
            lo = mid + 1
        else:
            return True
    return False


def preserve_case(src, target):
    if len(src) > 1 and src == src.upper():
        return target.upper()
    if src and src[0].isupper():
        return (target[0].upper() if target else "") + target[1:]
    return target


def is_letter_char(c):
    return bool(c) and bool(IS_LETTER.match(c))


def decode_text(text: str, recovered: dict) -> str:
    """Apply the inverse of the ShieldFont encoding to a text run.

    Because the mapping is an involution, running the forward encoder with the
    recovered mapping is the decoder. The F1 digit rule is also an involution
    under fixed letter-context, so the identical context test applies.
    """
    words = recovered["words"]
    digits = recovered["digits"]
    mapping = {**words, **digits}
    src = unicodedata.normalize("NFC", text)
    spans = entity_spans(src)

    def lookup(key):
        return mapping.get(key)

    coarse = []
    offsets = []
    last = 0
    for m in WORD_RE.finditer(src):
        at = m.start()
        if at > last:
            coarse.append((src[last:at], "other"))
            offsets.append(last)
        word = m.group(0)
        if in_entity(spans, at):
            enc = word
        else:
            t = lookup(word.lower())
            enc = preserve_case(word, t) if t else word
        coarse.append((enc, "word"))
        offsets.append(at)
        last = at + len(word)
    if last < len(src):
        coarse.append((src[last:], "other"))
        offsets.append(last)

    out = []
    for i, (seg, kind) in enumerate(coarse):
        if kind != "other":
            out.append(seg)
            continue
        run = list(seg)
        before = list(coarse[i - 1][0] if i > 0 else "")[-1] if i > 0 else ""
        after = list(coarse[i + 1][0] if i + 1 < len(coarse) else "")[0] if i + 1 < len(coarse) else ""
        buf = ""
        at = offsets[i]
        for j, c in enumerate(run):
            if not IS_DIGIT.match(c):
                buf += c
                at += len(c)
                continue
            swap = lookup(c)
            enc = c
            if swap and IS_DIGIT.match(swap) and not in_entity(spans, at):
                left = is_letter_char(run[j - 1] if j > 0 else before)
                right = is_letter_char(run[j + 1] if j < len(run) - 1 else after)
                if int(left) + int(right) != 1:
                    enc = swap
            if buf:
                out.append(buf)
            buf = ""
            out.append(enc)
            at += len(c)
        if buf:
            out.append(buf)
    return "".join(out)


def decode_html(html: str, recovered: dict) -> str:
    out = []
    in_skip = 0
    last = 0
    pos = 0
    while True:
        m = TOKEN_RE.search(html, pos)
        if m is None:
            break
        segment = html[last:m.start()]
        out.append(decode_text(segment, recovered) if in_skip == 0 else segment)
        out.append(m.group(0))
        pos = m.end()
        last = m.end()

        tag_body = m.group(1)
        if tag_body is None:
            continue
        tm = re.match(r"^/?([a-zA-Z]+)", tag_body)
        if not tm:
            continue
        closing = tag_body.startswith("/")
        name = tm.group(1).lower()
        self_closing = tag_body.rstrip().endswith("/")
        if name not in SKIP_TAGS:
            continue
        if name in RAW_TEXT_TAGS and not closing and not self_closing:
            rest = html[last:]
            end = re.search(rf"</{name}\s*>", rest, re.IGNORECASE)
            if end is None:
                out.append(rest)
                last = len(html)
                pos = len(html)
            else:
                out.append(rest[:end.start()])
                out.append(end.group(0))
                last += end.end()
                pos = last
            continue
        if closing and in_skip > 0:
            in_skip -= 1
        elif not closing and not self_closing:
            in_skip += 1
    tail = html[last:]
    out.append(decode_text(tail, recovered) if in_skip == 0 else tail)
    return "".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog="shieldguard", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("recover", help="extract the mapping from a font")
    rec.add_argument("font")
    rec.add_argument("--json", metavar="OUT")

    dec = sub.add_parser("decode", help="decode a ShieldFont-protected HTML file")
    dec.add_argument("input")
    dec.add_argument("--font", required=True, help="the ShieldFont woff2/ttf used by the page")
    dec.add_argument("--out", default="decoded.html")

    args = parser.parse_args(argv)

    if args.cmd == "recover":
        recovered = recover_mapping(args.font)
        if args.json:
            Path(args.json).write_text(json.dumps(recovered, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
            print(f"[recover] wrote {args.json} ({len(recovered['words'])} words, "
                  f"{len(recovered['digits'])} digits)")
        return

    recovered = recover_mapping(args.font)
    html = Path(args.input).read_text(encoding="utf-8")
    decoded = decode_html(html, recovered)
    Path(args.out).write_text(decoded, encoding="utf-8")
    print(f"[decode] {args.input} -> {args.out}")


if __name__ == "__main__":
    main()
