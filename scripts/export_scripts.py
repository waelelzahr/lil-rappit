"""One-off: copy script.json from downloaded run artifacts (in ./dl) into state/scripts/."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import writer  # noqa: E402
from rappit.common import EPISODES, ROOT, load_state  # noqa: E402

titles = {e["id"]: e["title"] for e in EPISODES}
state = load_state()
keep = ROOT / "state" / "scripts"
keep.mkdir(parents=True, exist_ok=True)
for f in sorted(Path("dl").rglob("script.json")):
    item_id = f.parent.name
    base = item_id.split("-v")[0] if "-v" in item_id[-4:] else item_id
    ep = state["items"].get(base, {}).get("episode", "")
    script = json.loads(f.read_text(encoding="utf-8"))
    (keep / f"{item_id}.json").write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    (keep / f"{item_id}.md").write_text(writer.readable(script, titles.get(ep, item_id)), encoding="utf-8")
    print("exported", item_id)
