"""Draw the reference portrait of any recurring character that doesn't have one yet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rappit import concepts, gen  # noqa: E402
from rappit.common import log  # noqa: E402


def main():
    for key, look in concepts.CAST.items():
        ref = concepts.ref_path(key)
        if ref.exists():
            continue
        ref.parent.mkdir(parents=True, exist_ok=True)
        gen.image(f"Character reference portrait of {look}. Full body and face clearly visible, "
                  "standing in a neutral pose, plain light-grey studio backdrop.", ref,
                  style=concepts.STYLE, with_rappit=False)
        log(f"made {ref.name}")


if __name__ == "__main__":
    main()
