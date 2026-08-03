# Threat Model

Answers to the spec's eight questions, based on the cloned repo, the shipped
fonts, and a working font-derived decoder.

## 1. Can the visible text be reconstructed from the font alone?

**Yes, fully.** The font must contain the complete substitution mapping for the
browser to render decoy text as readable text. Reading GSUB ligatures + glyf
composites + reverse cmap recovers every pair. Verified: 0 misses against all
four shipped variants. The maintainers' own README concedes "11,962 of 11,962
pairs recovered from our own shipped font, no dictionary needed."

## 2. Is repository source code necessary?

**No.** The decoder in `prototype/source/shieldguard.py` derives the mapping
entirely from the font binary. Repo source was used here to *validate* the
recovery against the shipped JSONs and to understand the scheme, but no shipped
mapping file is read at decode time.

## 3. Does a custom mapping materially improve resistance?

**Not against a per-page attacker.** Tested for real: a mapping generated from an
unseen seed (`reseed_mapping.py --seed 20260803`) and built into a brand-new
Arial-based font was recovered from that font with **0 misses in 1.34 s** — the
strongest variant the system can produce. A private mapping still ships inside
the font (the browser needs it to render), so the same table walker recovers it.
Custom mappings only help at *network* scale: defeating N mappings costs N font
inversions, and a private seed prevents reuse of a precomputed mapping. It raises
the cost of *mass* decoding, not of decoding any one page.

## 4. Are mappings exposed through GSUB?

**Yes, by design.** The word pairs live in GSUB LigatureSubst lookups and the
composite glyph components; the digit pairs in SingleSubst. The glyph *names* are
salted and dropped from the woff2, but the structural data the names would have
revealed is fully present in the tables themselves. Salting names and dropping the
`post` table adds friction for name-based recovery, not table-based recovery.

## 5. Can ShieldFont be automatically detected?

**Yes, multiple ways.** (a) The font's GSUB contains thousands of ligature rules
under `ccmp` plus the fire-then-revert ChainContext structure — an unmistakable
signature. (b) The CDN stylesheet URL names the project (`@shieldfont/font`). (c)
The `.tk9` class is a documented generic token. (d) `@font-face` family names like
"ShieldFont Optik". (e) Text whose rendered glyphs differ from its code points
(tested by shaping the font and comparing).

## 6. Can a browser-rendering pipeline recover the visible text?

**Yes.** The maintainers list headless browsers with font rendering (Playwright,
Puppeteer) under "does not defend against"; reading `innerText` after rendering
yields the visible text. This is the backup if table-parsing ever fails (exotic
custom GSUB layouts). Not needed here: the font-derived decoder is exact.

## 7. What computational cost does ShieldFont impose on a targeted decoder?

**Negligible, amortized.** Mapping recovery: ~0.8s per font once converted (a
one-time ~80s woff2→ttf for a first contact). Per-page decode: milliseconds
(linear tokenization + dict lookups). There is no secret, no key, and no
puzzle on the no-JS tiers; the real words are recoverable at scrape speed.

## 8. Which design choices meaningfully increase resistance?

Measured against the recovered font + decoder, *none of the current ones do*:

| choice | effect |
|---|---|
| salted glyph names | none (names not needed; dropped anyway) |
| `post` format 3.0 | none for table-based recovery; only blocks name-based guessing |
| fire-then-revert chains | none (attacker reads tables, not rendering) |
| per-variant reseeds | none per-page; raises mass-decoding cost only |
| custom mapping kept private | **none per-page — proven: unseen-seed font recovered with 0 misses** |

Choices that *could* raise cost (all cost-raising, none preventing):
- **Per-page/per-request font generation** with a fresh mapping (forces a font
  fetch + conversion + inversion per page instead of per-site).
- **More complex shaping** (contextual multi-step GSUB that is not plain
  ligatures) pushes an attacker toward the HarfBuzz/browser fallback — still
  automated, but more code.
- **Encryption + JS-only unlock** (the `screenReader` path) is the only design
  that keeps real words off the wire in readable-or-shapable form — at the price
  of requiring JavaScript, breaking WCAG 2.2 SC 1.3.1, and being solvable by
  any JS-running client.

## Bottom line

ShieldFont is an **obfuscation**, not a cipher. Its security model is economic
(network-wide diversity makes mass scraping costly), not cryptographic. For any
individual page, the plaintext is recoverable from the page's own resources —
the font alone suffices, and the decoder is ~300 lines.
