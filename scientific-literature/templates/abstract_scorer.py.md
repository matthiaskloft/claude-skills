# Template: `abstract_scorer.py`

```python
from pathlib import Path
import json
import yaml

CONFIG_PATH = Path("{{ config_path }}")
INPUT_PATH = Path("{{ input_path }}")
OUTPUT_PATH = Path("{{ output_path }}")

keywords = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["include_keywords"]
records = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

def score(text: str) -> int:
    lowered = text.lower()
    return sum(1 for kw in keywords if kw.lower() in lowered)

for record in records:
    record["prefilter_score"] = score(record.get("abstract", ""))

OUTPUT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
```
