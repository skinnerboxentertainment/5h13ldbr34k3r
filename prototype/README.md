# ShieldGuard Prototype

A generic, **font-only** decoder for ShieldFont-protected HTML.

Recovers the substitution mapping from the font's own GSUB + glyf tables (no
repository source, no hard-coded mapping), then applies the inverse
transformation while preserving HTML structure.

## How it works

1. **Recover the mapping** from the font:
   - reverse `cmap` (glyph → character),
   - GSUB `LigatureSubst` lookups (decoy-word glyphs → composite glyph),
   - `glyf` composites (composite → original-word letters).
   Result: `{decoy_word: original_word}` plus digit swaps. The word mapping is an
   **involution** (`m[m[x]] === x`), so decoding is re-encoding — the same
   algorithm runs both ways.
2. **Decode the HTML**: tokenize text runs (skipping `script/style/code/pre/
   textarea/svg/math/noscript/title/option` and character references), look up
   each word case-preservingly, apply the context-aware digit rule
   (`1568→1073` but `M15-EN` untouched), and re-emit the document verbatim
   otherwise.

## Usage

```bash
# decode a protected page (font is the page's ShieldFont woff2/ttf)
python prototype/source/shieldguard.py decode input.html \
    --font path/to/optik-a.woff2 \
    --out decoded.html

# just extract the mapping to JSON
python prototype/source/shieldguard.py recover path/to/optik-a.woff2 --json mapping.json
```

A woff2 is converted to a cached `.ttf` in `prototype/source/fonts/` on first
use (~80 s once); after that, mapping recovery is ~0.8 s and decoding is
milliseconds.

## Requirements

- Python 3.10+
- `fonttools`
- `regex`

```bash
pip install fonttools regex
```

## Validation

```bash
python prototype/tests/run_tests.py
```

Tests (13 checks, all green at `bfc772782195f6ea05b7cf3ed79dbbc788d903a4`):

- Mapping recovery matches the shipped dictionary for **alpha, beta, gamma,
  maxhide** — 0 misses each.
- Round-trip of canonical text, mixed case, punctuation, unknown words,
  context-aware digits, accented words.
- Wrong-mapping rejection (a maxhide page decoded with the alpha mapping fails).
- Full-page fixture decodes **byte-for-byte** to the original plaintext
  (`results/decoded.html == results/plain-page.html`).
- **Private mapping (the hardest case):** a mapping minted from an unseen seed
  and built into a brand-new Arial-based font is recovered with **0 misses in
  1.34 s** and round-trips a full sentence. Reproduce with
  `python prototype/tests/build_private_font.py`, then re-run the suite.

## Strategy comparison

| Strategy | outcome |
|---|---|
| A: repo mapping data | works instantly (mappings ship in the repo/CDN), but is mapping-specific |
| **B: GSUB extraction (this)** | **generic — works on any ShieldFont-built font; preferred** |
| C: browser rendering | works (maintainers concede it), unnecessary — B is exact |
