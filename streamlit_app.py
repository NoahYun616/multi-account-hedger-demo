from __future__ import annotations

import os

os.environ["HEDGER_CLOUD_PREVIEW"] = "true"

from dashboard import main


if __name__ == "__main__":
    main()
