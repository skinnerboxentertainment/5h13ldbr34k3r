/**
 * shieldguard-demo — browser port of the ShieldFont decoder.
 *
 * Applies the mapping recovered from a ShieldFont font's GSUB tables
 * (see prototype/source/shieldguard.py). Because the mapping is an
 * involution, "encode" and "decode" are the same operation.
 */
(function () {
  "use strict";

  const WORD_RE = /\p{L}+/gu;
  const IS_DIGIT = /^\d$/;
  const IS_LETTER = /\p{L}/u;
  const ENTITY_RE = /&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[a-zA-Z][a-zA-Z0-9]{1,31});/g;

  function entitySpans(s) {
    const spans = [];
    ENTITY_RE.lastIndex = 0;
    let m;
    while ((m = ENTITY_RE.exec(s)) !== null) spans.push([m.index, m.index + m[0].length]);
    return spans;
  }
  function inEntity(spans, i) {
    let lo = 0, hi = spans.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const a = spans[mid][0], b = spans[mid][1];
      if (i < a) hi = mid - 1;
      else if (i >= b) lo = mid + 1;
      else return true;
    }
    return false;
  }
  function preserveCase(src, target) {
    if (src.length > 1 && src === src.toUpperCase()) return target.toUpperCase();
    if (src[0] && src[0] === src[0].toUpperCase()) {
      return (target[0] ? target[0].toUpperCase() : "") + target.slice(1);
    }
    return target;
  }
  function isLetterChar(c) {
    return c !== undefined && c !== "" && IS_LETTER.test(c);
  }
  function own(mapping, key) {
    return Object.prototype.hasOwnProperty.call(mapping, key) ? mapping[key] : undefined;
  }

  /** Apply the recovered mapping once (encode or decode — same thing). */
  function transform(text, mapping) {
    const words = mapping.words || {};
    const digits = mapping.digits || {};
    const src = String(text).normalize("NFC");
    const spans = entitySpans(src);
    const coarse = [];
    const offsets = [];
    let last = 0;
    for (const m of src.matchAll(WORD_RE)) {
      const at = m.index;
      if (at > last) { coarse.push({ s: src.slice(last, at), kind: "other" }); offsets.push(last); }
      const word = m[0];
      let enc = word;
      if (!inEntity(spans, at)) {
        const t = own(words, word.toLowerCase());
        if (t) enc = preserveCase(word, t);
      }
      coarse.push({ s: enc, kind: "word" });
      offsets.push(at);
      last = at + word.length;
    }
    if (last < src.length) { coarse.push({ s: src.slice(last), kind: "other" }); offsets.push(last); }

    const out = [];
    for (let i = 0; i < coarse.length; i++) {
      const seg = coarse[i];
      if (seg.kind !== "other") { out.push(seg.s); continue; }
      const run = Array.from(seg.s);
      const before = Array.from(coarse[i - 1] ? coarse[i - 1].s : "").pop();
      const after = Array.from(coarse[i + 1] ? coarse[i + 1].s : "")[0];
      let buf = "";
      let at = offsets[i];
      for (let j = 0; j < run.length; j++) {
        const c = run[j];
        if (!IS_DIGIT.test(c)) { buf += c; at += c.length; continue; }
        const swap = own(digits, c);
        let enc = c;
        if (swap && IS_DIGIT.test(swap) && !inEntity(spans, at)) {
          const left = isLetterChar(j > 0 ? run[j - 1] : before);
          const right = isLetterChar(j < run.length - 1 ? run[j + 1] : after);
          if (Number(left) + Number(right) !== 1) enc = swap;
        }
        if (buf) out.push(buf);
        buf = "";
        out.push(enc);
        at += c.length;
      }
      if (buf) out.push(buf);
    }
    return out.join("");
  }

  /** Show which words the mapping actually rewrites (for the "x-ray" view). */
  function highlight(text, mapping) {
    const words = mapping.words || {};
    return String(text).normalize("NFC").replace(/\p{L}+/gu, (w) => {
      const t = words[w.toLowerCase()];
      if (!t || t === w) return w;
      return '<mark class="swapped">' + w + "</mark>";
    });
  }

  window.ShieldGuard = { transform, highlight };
})();
