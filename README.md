# 5h13ldbr34k3r

> **Proof-of-concept circumvention of ShieldFont's font-based text obfuscation.**
> This repository was **generated entirely via agentic AI coding** — from reading
> the upstream spec, cloning and analyzing the target, and building the decoder,
> to packaging and this page. It is defensive interoperability research against an
> open-source project that itself concedes font inversion defeats it.

A definitive, generic decoder for [ShieldFont](https://github.com/isaqueseneda/shieldfont)-protected
HTML. Reconstructs the human-visible text from ShieldFont's encoded page source
using **only the page's own font** — no dictionary, no repository source, no
hard-coded mapping.

ShieldFont replaces content words in your HTML with plausible decoys and ships a
font whose OpenType GSUB rules re-shape those decoys into readable glyphs.
Humans see the original; scrapers read the decoy. The load-bearing fact is that
**the browser needs the entire substitution table, so the entire table ships in
the font.** 5h13ldbr34k3r recovers it from the font tables and inverts it.

## How fast is this defeat?

Measured from real timestamps (2026-08-03): **~9 minutes** from cloning the
upstream repository to a working proof-of-concept decoder that recovered the
visible text from a ShieldFont-protected page **byte-for-byte**. The complete
validated package (all four shipped variants + the private-mapping hardest case,
0 misses) was finished in **~26 minutes**. The decoder itself is ~300 lines.
This is the practical point: the "protection" is a reversible text
transformation, and reversing it is minutes of work, not a research project.

## Results

Verified against the shipped fonts at
`isaqueseneda/shieldfont` @ `bfc772782195f6ea05b7cf3ed79dbbc788d903a4`:

| variant | word pairs recovered | checked vs shipped | misses |
|---|---|---|---|
| alpha | 11,962 | 11,962 | **0** |
| beta | 12,026 | 12,026 | **0** |
| gamma | 12,028 | 12,028 | **0** |
| maxhide | 2,528 | 2,528 | **0** |
| **private (unseen seed, fresh font)** | **11,966** | **11,966** | **0** |

The private-mapping row is the strongest case the system can produce: a mapping
generated from a seed no attacker is given, built into a brand-new font. It is
recovered with 0 misses in ~1.3 s. Full page fixtures decode **byte-for-byte**.

The `screenReader` accessibility path ships the real words encrypted behind a
Rivest–Shamir–Wagner time-lock puzzle. It is not cryptographically bypassed —
but it holds the same words already recovered from the font, and OCR recovers
them for ~5 CPU-seconds/page regardless (per the maintainers' own threat model).

## Live demo

[**See it work**](https://skinnerboxentertainment.github.io/5h13ldbr34k3r/) — a
GitHub Pages page that demonstrates both sides of the trick in your browser:

- the **poison**: a sentence encoded the way ShieldFont encodes it (what a
  scraper reads in the HTML), rendered through the *real* ShieldFont webfont so
  you see it as the human does;
- the **solver**: type any sentence and watch it encoded and decoded live,
  using the mapping this project recovered from the font.

The mapping used by the page (`docs/assets/alpha-mapping.json`) was derived by
`shieldguard` from the real `optik-a.woff2` — no dictionary copied from the
upstream repo. Run it in the browser: open `docs/index.html` or deploy `docs/`
to GitHub Pages (a workflow is included).

## Quick start

```bash
pip install fonttools regex

# decode a protected page
python prototype/source/shieldguard.py decode input.html \
    --font path/to/optik-a.woff2 \
    --out decoded.html

# just extract the mapping from a font
python prototype/source/shieldguard.py recover path/to/optik-a.woff2 --json mapping.json
```

A `.woff2` is converted to a cached `.ttf` once (~80 s); afterwards mapping
recovery is ~1 s and per-page decode is milliseconds.

## Tests

```bash
python prototype/tests/run_tests.py      # 13 checks, all green
python prototype/tests/build_private_font.py   # build the hardest-case fixture
```

## How it works

1. **Recover** `{decoy_word: original_word}` from the font: reverse `cmap` +
   GSUB `LigatureSubst` lookups + `glyf` composite components. Digit/single-char
   swaps come from `SingleSubst` lookups (extension-wrapped or not).
2. **Decode** HTML by tokenizing text runs (skipping
   `script/style/code/pre/textarea/svg/math/noscript/title/option` and character
   references), looking up each word case-preservingly, and applying the
   context-aware digit rule (`1568→1073`, but `M15-EN` untouched).

The word mapping is an **involution** (`m[m[x]] === x`), so decode is literally
re-encode — the same algorithm runs both ways, which is also how fixtures are
built.

## Repository layout

```
research/    architecture.md · findings.md · limitations.md · threat-model.md
prototype/   source/shieldguard.py · tests/run_tests.py · tests/build_private_font.py
docs/        index.html · assets/decoder.js · assets/alpha-mapping.json  (GitHub Pages demo)
results/     encoded.html · decoded.html · plain-page.html · test-results.json
shieldfont/  the cloned upstream repo (analysis + fixture building only)
```

## Scope and ethics

This is defensive interoperability research. It was conducted only against the
cloned upstream repository and locally generated pages — never against unrelated
third-party sites. ShieldFont is open source (AGPL-3.0) and its own documentation
concedes that font inversion defeats it; this project is that concession,
implemented and measured. No authentication or authorization is bypassed.

5h13ldbr34k3r's value is defensive: site owners who adopt ShieldFont should know
exactly what it does and does not protect, and anyone who sees "protected"
content should be able to recover the text they are entitled to read.

## License

AGPL-3.0 (matches the upstream project this analyzes). The shipped `optik-*.woff2`
fonts are Optik (© Playtype), licensed to ShieldFont under their NOTICE; this
repository does not redistribute those font outlines — the decoder reads them,
it does not copy them.
