# V6 cross-Act reference provenance

The V1–V5 parser preserves unresolved cross-Act references in
`section_refs.to_act_name` and `to_section_no`. V6 adds a deterministic resolver
that matches those values against the latest indexed compilation without
rewriting the original reference text.

Subsection references such as `182(4)` and `172(1)(a)` are linked to the parent
section node (`182` and `172`) because the current section parser stores the
parent as the retrievable evidence unit. The raw subsection identifier remains
available in `to_section_no` and `ref_text` for display and later finer-grained
parsing.

The latest local run resolved **362** additional cross-Act references. The V6
projection now contains **723** `cross_ref` edges, alongside typed
`defines`, `delegates` and `overrides` edges. Reproduce the integrity check with:

```bash
python -m scripts.check_cross_act_refs_v6
```
