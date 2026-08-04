# Direction from reference — template (awwwards-reference pack)

Filled by visual-director when the user picks a cached reference at
calibration (K2B only — hard stop: never feeds K2A base skin).

```yaml
direction:
  id: <direction-id>
  seed:
    source: awwwards-reference
    reference_id: <arch-...>            # from search-references.py
    source_note: <attribution line>
  dials: {variance: <0-10>, motion: <0-10>, density: <0-10>}
  axes:
    composition: <decision from tokens_hint + project content>
    type_voice: <decision>
    color: <palette logic — extracted draft tokens, curated into layers>
    surface: <decision>
    shape: <decision>
    imagery: <decision>
    motion: <decision within motion-budgets>
  extracted_tokens: artifacts/visual/<id>-tokens-draft.json   # optional
  budget_check: <warn lines if extracted values break LCP/CLS/INP targets>
  ai_look_scan: pass | fail(<markers>)   # ai-look-detector on the slice
```

Rules:

1. The reference contributes PRINCIPLES + CSS facts (tokens) — never
   markup, imagery, or copy (license_notes in pack.yaml).
2. Extracted drafts are curated into primitive/semantic layers by the
   direction author; component tokens reference semantic only [A.21].
3. The user sees at most 3 candidates (hard stop) and may refuse all —
   refusal = calibration falls back to category anchors + base skin.
