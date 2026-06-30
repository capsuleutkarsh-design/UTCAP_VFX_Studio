"""Shared async thumbnail loader used by dashboard UI components."""

import logging
import weakref

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QImage

try:
    import shiboken6
except Exception:
    shiboken6 = None

logger = logging.getLogger(__name__)


def _is_qobject_alive(obj):
    if obj is None:
        return False
    if shiboken6 is None:
        return True
    try:
        return shiboken6.isValid(obj)
    except Exception:
        return True


class ImageLoaderSignals(QObject):
    started = Signal(str)  # identifier
    finished = Signal(str, str, QImage)  # identifier, path, image


class ImageLoaderTask(QRunnable):
    def __init__(self, thumb_gen, identifier, project_code, reel, shot, project_root=""):
        super().__init__()
        self.thumb_gen = thumb_gen
        self.identifier = identifier
        self.project_code = project_code
        self.reel = reel
        self.shot = shot
        self.project_root = project_root
        self.signals = ImageLoaderSignals()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self._cancelled:
            return

        # Emit started signal (yellow/loading state in dashboard)
        try:
            self.signals.started.emit(self.identifier)
        except RuntimeError:
            return

        if self._cancelled:
            return

        path = self.thumb_gen.get_or_create_thumbnail(
            self.project_code, self.reel, self.shot, self.project_root
        )
        if self._cancelled:
            return
        image = QImage(path) if path else QImage()
        try:
            self.signals.finished.emit(self.identifier, path or "", image)
        except RuntimeError:
            return


class AsyncImageLoader(QObject):
    image_started = Signal(str)
    image_loaded = Signal(str, str, QImage)

    def __init__(self, thumb_gen):
        super().__init__()
        self.thumb_gen = thumb_gen
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)
        self._shutdown = False
        self._active_tasks = set()

    def _track_task(self, task):
        self._active_tasks.add(task)
        task_ref = weakref.ref(task)

        def _release(*_args):
            tracked = task_ref()
            if tracked is not None:
                self._active_tasks.discard(tracked)

        task.signals.finished.connect(_release)
        return _release

    def load_image(self, identifier, project_code, reel, shot, project_root=""):
        if self._shutdown:
            return
        if not _is_qobject_alive(self):
            return

        task = ImageLoaderTask(self.thumb_gen, identifier, project_code, reel, shot, project_root)
        self._track_task(task)
        task.signals.started.connect(self.on_image_started)
        task.signals.finished.connect(self.on_image_loaded)
        self.thread_pool.start(task)

    def on_image_started(self, identifier):
        if self._shutdown or not _is_qobject_alive(self):
            return
        self.image_started.emit(identifier)

    def on_image_loaded(self, identifier, path, image):
        if self._shutdown or not _is_qobject_alive(self):
            return
        self.image_loaded.emit(identifier, path, image)

    def shutdown(self, timeout_ms: int = 2000):
        self._shutdown = True
        for task in list(self._active_tasks):
            try:
                task.cancel()
            except Exception as exc:
                logger.debug("Image loader task cancel warning: %s", exc)
        try:
            self.thread_pool.waitForDone(timeout_ms)
        except Exception as exc:
            logger.debug("Image loader shutdown warning: %s", exc)
        self._active_tasks.clear()

