---
name: lit-plan
description: Initialize literature config and search strategy.
---

# lit-plan

1. Collect project description and target scope.
2. Ensure `litreview.yaml` exists with tracked repo paths.
3. Scaffold `litreview/` YAML files: `categories.yaml`, `search_profiles.yaml`, `title_patterns.yaml`, `abstract_keywords.yaml`, `crawl_config.yaml`.
4. Create `.lit-cache.json` locally (gitignored) for Zotero paths.
5. Offer CLAUDE.md integration:
   - Pointer line to `lit-guide`
   - Compact inlined rules
