import asyncio
import signal

from core.config_loader import ConfigManager
from core.engine import HedgeEngine
from core.utils import setup_logging


def main() -> None:
    setup_logging()
    asyncio.run(async_main())


async def async_main() -> None:
    cfg = ConfigManager(config_dir="config")
    await cfg.start()

    engine = HedgeEngine(cfg)
    await engine.start()

    stop_event = asyncio.Event()

    def _stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    await stop_event.wait()
    await engine.stop()
    await cfg.stop()