# `litreview.yaml` Reference

```yaml
project:
  name: "repo_name"
  description: "project topic"
  user_agent: "Project/1.0"

paths:
  references_dir: "docs/references"
  references_md: "docs/references.md"
  pipeline_data: "litreview/pipeline_data"
  fulltexts_dir: "litreview/fulltexts"
```

Heavy configuration lives in `litreview/*.yaml` and is loaded only by steps that need it.
