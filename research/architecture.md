# ShieldFont Architecture

Target: `isaqueseneda/shieldfont` @ `bfc772782195f6ea05b7cf3ed79dbbc788d903a4` (v0.3.2).

## Data flow

```text
Original Text
    ↓  (Node/build-time, packages/core/src/encode.ts)
ShieldFont Encoder  (word substitution + digit rotation, case-preserving)
    ↓
Encoded HTML  (decoy words in the page source)
    ↓
OpenType GSUB  (font's LigatureSubst + ChainContext "fire-then-revert")
    ↓
Rendered Human Text  (composite glyphs shaped like the originals)
```

## Encoding (packages/core/src/encode.ts)

- **Word substitution.** `WORD_RE = /\p{L}+/gu` tokenizes text into Unicode letter
  runs. Each run is looked up (lowercased) in the mapping dict; a match is replaced
  with its partner, then case is re-applied (`preserveCase`): all-caps → all-caps,
  title-case → title-case, else as-is.
- **Digit rotation.** Digits outside character references are permuted when they
  have **0 or 2 letter-neighbours**; left alone with exactly 1 (so `M15-EN`,
  `iPhone15`, `H3O` survive, while standalone `1568` → `1073`). Pairs: `0↔5`,
  `3↔8`, `4↔9`, `6↔7`.
- **HTML safety.** Character references (`&copy;`, `&#x2019;`) and
  `script/style/code/pre/textarea/svg/math/noscript/title/option` contents are
  never touched. Tag structure is preserved exactly.
- **The mapping is an involution**: `m[m[x]] === x` for all pairs (verified:
  11,970/11,970 for alpha). Therefore **`decode()` literally calls `encode()`** —
  encode-twice is identity. This single property is what makes the whole scheme
  reversible with zero extra work.

## Mappings (packages/core/src/mappings/*.json)

| variant | font | pairs | notes |
|---|---|---|---|
| `alpha` | `optik-a.woff2` | 11,970 | production default (CDN + package) |
| `beta` | `optik-b.woff2` | 12,034 | re-seed 1 |
| `gamma` | `optik-c.woff2` | 12,036 | re-seed 2 |
| `m15en` | `optik-m.woff2` | 2,534 | "maxhide", higher coverage |

Keys are lowercase source words; values are their same-POS, similar-frequency
decoy partners. The `_meta` block records provenance (seed 42 for alpha).

## Font generation (scripts/generate_font.py)

Given a base TTF + mapping, the generator:

1. Builds one **composite glyph** per word (`create_composite_glyph`), named
   `word.<sha1(salt|word)[:16]>` — the composite is literally the **original**
   word's letters laid out side by side.
2. Creates **GSUB LigatureSubst** rules (Type 4, wrapped in Extension Type 7)
   whose **input** is the *decoy* word's glyphs and whose **output** is that
   composite. Case variants `.cap` and `.upper` are added.
3. Adds **SingleSubst** (Type 1) rules for single-character (digit) pairs.
4. Implements the **"fire-then-revert"** word-boundary pattern:
   - Lookup A: every ligature fires unconditionally.
   - Lookup C: a MultipleSubst that *reverts* `word.X → input chars`.
   - Lookups D/E: ChainContext (Type 6, Fmt 3) that invoke C when the substituted
     glyph has a **letter neighbour** — i.e. it fired inside a larger word.
   - A/B/D/E are wired into the `ccmp` feature; C is internal-only.
5. Drops the `post` table to format 3.0 on the woff2 (no glyph names shipped).

## Runtime integration

- **React tier** (`<Shield>`): encodes server-side (RSC/build), emits the encoded
  text inside `aria-hidden`, loads the font, and can embed a client-side
  time-lock puzzle containing the real words (a separate, JS-gated path).
- **CDN tier**: `@shieldfont/font` ships `shieldfont-encoder.js` (a generated
  standalone bundle that **exports `encode`, `decode`, and `alpha`**) plus
  `shieldfont.css` and the four `optik-*.woff2` files.

## Where the defense actually lives

Not in any server, and not in a key: the browser must be able to turn decoy text
into readable glyphs, so the *entire substitution table ships to the client in
the font*. That is the load-bearing fact for the decoder.
