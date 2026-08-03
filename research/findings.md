# Findings

## The mapping is fully recoverable from the font alone

Reading the woff2/ttf with fontTools:

1. **Reverse cmap** maps every glyph back to its character(s).
2. **GSUB LigatureSubst** lookups yield, for each rule, the input glyph sequence
   (the *decoy* word) and the output composite glyph.
3. **glyf composites** for those output glyphs list the component glyphs — the
   *original* word's letters.

Combining the three gives `{decoy_word: original_word}` with **no repository
source needed**. Recovery quality, verified against the shipped `alpha/beta/
gamma/m15en.json`:

| variant | pairs recovered | digit swaps | checked vs shipped | misses |
|---|---|---|---|---|
| alpha | 35,886 (11,962 words × 3 case) | 38 | 11,962 | **0** |
| beta | 36,078 | 38 | 12,026 | **0** |
| gamma | 36,084 | 38 | 12,028 | **0** |
| maxhide | 7,584 | 36 | 2,528 | **0** |

Recovery of the README's canonical examples is exact: `belongs→determines`,
`protect→complain`, `words→previews`.

## decode == encode

Because every pair satisfies `m[m[x]] === x`, the decoder is the encoder run a
second time. There is no separate inverse to derive. `decode_text` applies the
forward algorithm (word lookup + case preservation + F1 digit rule) using the
recovered mapping, and it both decodes decoy text **and** re-encodes plaintext —
which is also how the fixtures were produced.

## Digit rule is context-aware and invertible

- `1568` → `1073` (standalone run: every digit swaps).
- `M15-EN` → `M10-EN`, `iPhone15` → `iPhone10` (letter-adjacent digits stay).
- `H3O`, `C4H10` untouched.
The rule is an involution under fixed letter-context, so the same test
(0-or-2 letter-neighbours → swap, 1 → leave) is used in both directions.

## HTML structure preservation

The decoder reuses the encoder's tokenizer: text between tags is transformed,
tags/attributes/comments pass through byte-identical, and `script`, `style`,
`code`, `pre`, `textarea`, `svg`, `math`, `noscript`, `title`, `option`
contents are never touched (matching `SKIP_TAGS`). A full-page fixture
round-trips **byte-for-byte** (`decoded.html == plain-page.html`, 964 bytes).

## Wrong-mapping rejection

Decoding a maxhide-encoded page with the alpha-derived mapping does **not**
reproduce the plaintext — the recovered mapping is specific to the font that
shipped it. A decoder must identify *which* font the page uses (or try the
detected one), which is exactly how a real attacker would operate.

## Three additional attack surfaces (beyond the font)

1. **The CDN encoder bundle ships `decode` and the full mapping.**
   `packages/font/shieldfont-encoder.js` exports `encode`, `decode`, `alpha` —
   any page using the CDN tier already publishes the decoder to the client.
2. **The mappings ship in the npm packages** (`@shieldfont/core`), so any site
   depending on them ships the dictionary.
3. **The `_meta` salt is derived, not secret.** `sha1("shieldfont/glyph-names/v1|"
   + mappingId)`. For published mappings the mappingId is public; glyph names
   would be guessable — moot here because the woff2 drops them entirely.

## The "fire-then-revert" GSUB is decoy-proof, not attacker-proof

The elaborate ChainContext reverts only exist to make *the font's own rendering*
respect word boundaries. An attacker who reads the font tables sees the full
mapping regardless; the revert logic is irrelevant to recovery. Its only effect
on the decoder is confirming that substitution applies to standalone letter-runs
— which the encoder's tokenizer already models.

## The strongest case is beaten: private/custom mappings

A defender's best play is a *private* mapping nobody outside their build has
seen (via `reseed_mapping.py` or their own dictionary). That claim was tested
for real:

1. `reseed_mapping.py --seed 20260803` minted a private mapping (11,974 pairs,
   100% involutive) — the dictionary an attacker would never be given.
2. `generate_font.py` built a **brand-new font from Arial** using that mapping
   (a fresh typeface, not one of the shipped four).
3. The decoder recovered the mapping from that font alone:

| private-mapping result | value |
|---|---|
| word pairs recovered | 36,049 (11,966 lowercase pairs) |
| tested against the private dictionary | 11,966 |
| misses | **0** |
| recovery time | 1.34 s |
| full-sentence round-trip | true |

A custom/private seed changes **nothing** — the mapping must still ship inside
the font for the browser to render it, so table recovery is seed-agnostic by
construction. This also surfaced the one robustness fix needed: a repacker can
wrap the digit `SingleSubst` in an Extension (Type 7) lookup, so the walker
unwraps extensions uniformly for all base lookup types rather than assuming
Type 1 stays bare.

The maintainers' own `reseed_mapping.py` docstring concedes exactly this:
*"the font you serve still encodes your pairs, so anyone who downloads it can
invert THAT font and recover your originals, seed or no seed."* The proof above
is that claim, executed.
