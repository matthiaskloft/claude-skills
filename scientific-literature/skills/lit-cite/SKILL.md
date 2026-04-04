---
name: lit-cite
description: Add citation to `_index.json` and regenerate references.md.
---

# lit-cite

Run:

```bash
python scientific-literature/scripts/cite.py "<doi>" --index "<references_dir>/_index.json" --references-md "<references_md>"
```

If DOI already exists, return the existing citekey without overwrite.
