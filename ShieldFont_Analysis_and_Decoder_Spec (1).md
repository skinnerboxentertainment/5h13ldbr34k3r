# Agent Specification: ShieldFont Analysis and Decoder Prototype

## Objective

Clone the open-source ShieldFont repository, determine precisely how its
encoder and OpenType substitution system transform source text into
human-readable rendered text, and build a local proof-of-concept decoder
that reconstructs the visible text from ShieldFont-protected HTML.

This is an interoperability and defensive research exercise. Work only
against the cloned repository, its included examples, the official
demonstration material, and locally generated test pages.

------------------------------------------------------------------------

## Repository

Clone:

``` bash
git clone https://github.com/isaqueseneda/shieldfont.git
cd shieldfont
git rev-parse HEAD
```

Record the commit hash used throughout the analysis.

------------------------------------------------------------------------

## Phase 1 -- Reverse Engineer the Architecture

Determine:

-   How text is encoded.
-   Where mapping tables are stored or generated.
-   How fonts are generated.
-   How GSUB/OpenType substitution is implemented.
-   Runtime JavaScript and React integration.
-   CSS/font loading behavior.
-   Build pipeline.

Produce a data-flow diagram:

``` text
Original Text
    ↓
ShieldFont Encoder
    ↓
Encoded HTML
    ↓
OpenType GSUB
    ↓
Rendered Human Text
```

------------------------------------------------------------------------

## Phase 2 -- Recover the Mapping

Determine whether mappings can be reconstructed from:

-   Source code
-   Generated fonts
-   GSUB tables
-   Runtime JavaScript
-   Build artifacts
-   CSS
-   Browser-loaded font resources

Document whether mappings are:

-   Static
-   Generated
-   Randomized
-   Embedded in the font
-   Recoverable without repository source

Use tools such as FontTools (TTX) or HarfBuzz where appropriate.

------------------------------------------------------------------------

## Phase 3 -- Build a Decoder

Implement a prototype:

``` bash
shieldfont-decode input.html
```

that produces:

``` bash
decoded.html
```

The decoder should:

1.  Parse HTML.
2.  Detect ShieldFont usage.
3.  Locate the associated font.
4.  Recover the substitution mapping.
5.  Apply the inverse transformation.
6.  Preserve HTML structure.
7.  Report unresolved substitutions.

Prefer deriving mappings directly from the font rather than relying on
repository source.

------------------------------------------------------------------------

## Phase 4 -- Evaluate Multiple Approaches

### Strategy A

Reverse using repository mapping data.

### Strategy B

Extract GSUB substitutions directly from the font and invert them.

### Strategy C

Render locally in a browser and recover the visible text using browser
rendering or accessibility APIs (not OCR unless used only as a
comparison baseline).

------------------------------------------------------------------------

## Phase 5 -- Validation

Generate local fixtures containing:

-   Official examples
-   Newly encoded text
-   Mixed capitalization
-   Punctuation
-   Unknown words
-   Custom mappings (if supported)

Measure:

-   Recovery accuracy
-   False substitutions
-   Processing speed
-   Source-code dependency
-   Font dependency

------------------------------------------------------------------------

## Deliverables

``` text
research/
    architecture.md
    findings.md
    limitations.md
    threat-model.md

prototype/
    README.md
    source/
    tests/

results/
    test-results.json
    encoded.html
    decoded.html
```

------------------------------------------------------------------------

## Threat Model

Answer the following:

1.  Can the visible text be reconstructed from the font alone?
2.  Is repository source code necessary?
3.  Does a custom mapping materially improve resistance?
4.  Are mappings exposed through GSUB?
5.  Can ShieldFont be automatically detected?
6.  Can a browser-rendering pipeline recover the visible text?
7.  What computational cost does ShieldFont impose on a targeted
    decoder?
8.  Which design choices meaningfully increase resistance?

------------------------------------------------------------------------

## Success Criteria

The project succeeds when an automated tool can reconstruct the
human-visible text from ShieldFont-protected HTML using information
derived from the associated font and page resources.

The preferred outcome is a generic decoder that works against arbitrary
ShieldFont-generated fonts rather than relying on hard-coded mappings.

------------------------------------------------------------------------

## Constraints

-   Work only against the cloned repository and locally generated
    examples.
-   Do not target unrelated third-party websites.
-   Do not bypass authentication or authorization.
-   Preserve upstream licensing and attribution.
-   Clearly distinguish verified findings from assumptions.

------------------------------------------------------------------------

## Final Instruction

Treat ShieldFont as a reversible text-transformation and font-shaping
system. Fully document the encoding pipeline, analyze the generated font
tables, derive an inverse decoding process, implement a working proof of
concept, and explain precisely which implementation details make the
protection recoverable and where its practical limits lie.
