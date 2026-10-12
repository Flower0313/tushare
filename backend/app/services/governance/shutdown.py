from __future__ import annotations

import asyncio
import signal


def install_shutdown_signals(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for name in ("SIGINT", "SIGTERM"):
        value = getattr(signal, name, None)
        if value is None:
            continue
        try:
            loop.add_signal_handler(value, request_stop)
        except (NotImplementedError, RuntimeError):
            signal.signal(value, lambda *_: loop.call_soon_threadsafe(request_stop))
