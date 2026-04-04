---
name: lit-acquire
description: Acquire full text via Zotero, OpenAlex OA, or arXiv fallback.
---

# lit-acquire

Run:

```bash
python scientific-literature/scripts/acquire.py --title "<title>" --doi "<doi>" --openalex-id "<id>" --dest "<references_dir>"
```

Search order:
1. Zotero SQLite
2. Zotero PDF filename scan
3. OpenAlex OA URL
4. arXiv
