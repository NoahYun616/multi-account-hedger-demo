from __future__ import annotations

import os

os.environ["HEDGER_DEMO_MODE"] = "true"

from dashboard import main


if __name__ == "__main__":
    main()
