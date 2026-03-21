from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.signals.finished.emit(result)
        except Exception as exc:  # Surface friendly message in UI.
            self.signals.failed.emit(str(exc))


class AsyncRunner:
    def __init__(self) -> None:
        self._pool = QThreadPool.globalInstance()

    def run(self, fn: Callable[..., Any], on_done: Callable[[Any], None], on_error: Callable[[str], None], *args: Any, **kwargs: Any) -> None:
        worker = _Worker(fn, *args, **kwargs)
        worker.signals.finished.connect(on_done)
        worker.signals.failed.connect(on_error)
        self._pool.start(worker)
