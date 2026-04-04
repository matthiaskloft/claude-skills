# Source-Backed Implementation

- Verify references against authoritative metadata sources before adding them.
- Never invent DOI, venue, or year fields.
- Keep `_index.json` as the write target; regenerate `references.md` from it.
- Track acquisition provenance in `source` as a list (e.g. `["zotero"]`, `["openalex_oa"]`).
