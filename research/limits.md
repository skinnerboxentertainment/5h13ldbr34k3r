# Limitations

## Verified as out of scope / not addressed

- **Browser-rendered recovery (Strategy C)** was not needed: Strategy B (font
  tables) is exact and cheaper. A headless-browser/accessibility path would still
  work (the maintainers concede Playwright/Puppeteer with font rendering defeats
  the scheme) but adds no correctness over the font-derived mapping.
- **The `screenReader` time-lock puzzle** is not bypassed. It is a genuine
  Rivest–Shamir–Wagner time-lock (2048-bit modulus, fresh primes per block,
  AES-256-GCM, trapdoor discarded) calibrated to ~0.97 CPU-s/block — just under
  the OCR floor — so it is not faster to solve than sequential squaring. This is
  not a gap in the attack: the puzzle holds the *same* words already recovered
  from the font, and OCR recovers them for ~5 CPU-s/page regardless. It matters
  only for a page that (a) runs the React tier with `screenReader` on and
  (b) chooses the puzzle path over the font or OCR path.

## Decoder scope

- **Single-mapping pages.** The decoder assumes the page (or region) uses one
  ShieldFont variant. A page mixing `alpha` and `maxhide` blocks needs per-element
  font detection; the mapping itself is still recoverable per font.
- **Mapping identity.** We recover from the *font file* directly. Detecting which
  font a page uses automatically (CSS `font-family`, `@font-face` src, class
  names) is the integration step; the current CLI takes `--font`.
- **No OCR.** Purely table-based; no rendering, no screenshots.
- **Custom fonts with different internals.** If someone builds a ShieldFont with a
  radically different GSUB layout (contextual substitution chains that aren't
  plain ligatures), the generic walker may need extension. The shipped four
  variants and the generator's single pattern all parse cleanly. A HarfBuzz-shaping
  fallback (compare shaped glyph IDs against the input) would cover exotic cases.
- **Non-involutive custom mappings.** A private mapping that is not an involution
  would break "decode == encode" and require a genuine inverse table. `make_injective`
  only guarantees injectivity, not involutivity — but a private reseed built
  through `reseed_mapping.py` remains a bijection of pairs, so the ligature
  table still contains the full mapping in both directions.

## Known structural weaknesses in the target (not ours to fix)

- Encoding happens at most once; function words and out-of-dictionary words pass
  through untouched, so an encoded page is ~2/11 words different from plaintext
  — visible if you already know the plaintext, and reversible wholesale.
- The dictionary is static per variant; frequency analysis on a corpus can
  identify decoys.
- Forced fonts (user agent overriding `font-family`) render decoys as plain text
  — a human-visible leak with no decoder needed.
- The `screenReader` path seals plaintext into the page behind a JS time-lock;
  a scraper that runs JS could solve the puzzle and read the real words without
  touching the font.

## Performance

- First decode of a fresh woff2 requires a woff2→ttf conversion (fontTools'
  pure-Python woff2 glyf reconstruction ~80s). Cached as `prototype/source/fonts/
  *.ttf`, subsequent mapping recoveries take **~0.8s** and per-page decode is
  milliseconds. Real-world pages would fetch and convert the font once, then
  amortize.
