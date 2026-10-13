# damned_waters/tools/citygen/build_city.py
# Purpose: regenerate the city's room files (game/data/rooms) from the area generators, in the order
# they depend on each other (each later area opens its way in through an earlier one's rooms).
# area2 (Thorbeckeplein, Rembrandtplein) is kept for reference only: its rooms carry later hand edits.
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ["area3", "area4", "area5", "area6", "area7", "area8"]


KEPT = ["thorbeckeplein", "rembrandtplein", "herengracht"]   # rooms made before the generators: dressed in place


def main(argv=None):
    sys.path.insert(0, str(HERE))
    for name in argv or ORDER:
        print(f"[citygen] {name}")
        runpy.run_path(str(HERE / f"{name}.py"), run_name="__main__")
    import json
    import common
    import aftermath13
    for rid in aftermath13.STORIES:
        f = Path(common.R) / f"{rid}.json"
        spec = json.loads(f.read_text())
        aftermath13.apply(spec)
        f.write_text(json.dumps(spec, indent=2, ensure_ascii=True) + "\n")
    for rid in KEPT:
        f = Path(common.R) / f"{rid}.json"
        spec = json.loads(f.read_text())
        common.dress_street(spec)
        if spec.get("outdoor"):
            spec["ambience"] = "amb_street_rain"
        f.write_text(json.dumps(spec, indent=2, ensure_ascii=True) + "\n")
    import interiors
    for rid in interiors.ROOMS:   # the interior pass: the shops' stock, fixtures and signs
        f = Path(common.R) / f"{rid}.json"
        spec = json.loads(f.read_text())
        interiors.apply(spec)
        f.write_text(json.dumps(spec, indent=2, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
