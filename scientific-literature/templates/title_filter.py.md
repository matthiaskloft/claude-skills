# Template: `title_filter.py`

Use this template when generating a project-specific title filter wrapper.

```python
from pathlib import Path
import json
import re
import yaml

CONFIG_PATH = Path("{{ config_path }}")
INPUT_PATH = Path("{{ input_path }}")
OUTPUT_PATH = Path("{{ output_path }}")

patterns = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["include_patterns"]
records = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
filtered = [r for r in records if any(rx.search(r.get("title", "")) for rx in compiled)]
OUTPUT_PATH.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
```
