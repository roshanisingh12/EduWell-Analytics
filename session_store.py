"""
EduWell Analytics - per-browser analysis sessions.

Keeps each visitor's uploaded analysis in memory, keyed by a session cookie,
with an idle timeout and a cap on concurrent sessions (least recently used
sessions are evicted first). Evicted results delete their work folder.

State is held in process memory, so run the API as a single worker process.
"""

import threading
import time
from collections import OrderedDict
from typing import Optional, Tuple

from analysis_service import AnalysisResult


class SessionStore:
    def __init__(self, ttl_seconds: float, max_sessions: int):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._items: "OrderedDict[str, Tuple[AnalysisResult, float]]" = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._items)

    def get(self, sid: str) -> Optional[AnalysisResult]:
        with self._lock:
            item = self._items.get(sid)
            if item is None:
                return None
            result, last_seen = item
            if time.monotonic() - last_seen > self.ttl_seconds:
                del self._items[sid]
                expired = result
            else:
                self._items[sid] = (result, time.monotonic())
                self._items.move_to_end(sid)
                return result
        expired.dispose()
        return None

    def put(self, sid: str, result: AnalysisResult) -> None:
        stale = []
        with self._lock:
            old = self._items.pop(sid, None)
            if old is not None:
                stale.append(old[0])
            self._items[sid] = (result, time.monotonic())
            while len(self._items) > self.max_sessions:
                _, (evicted, _) = self._items.popitem(last=False)
                stale.append(evicted)
        for item in stale:
            item.dispose()

    def drop(self, sid: str) -> None:
        with self._lock:
            item = self._items.pop(sid, None)
        if item is not None:
            item[0].dispose()

    def prune(self) -> int:
        """Removes expired sessions and returns how many were removed."""
        now = time.monotonic()
        with self._lock:
            expired = [sid for sid, (_, seen) in self._items.items() if now - seen > self.ttl_seconds]
            results = [self._items.pop(sid)[0] for sid in expired]
        for result in results:
            result.dispose()
        return len(results)

    def clear(self) -> None:
        with self._lock:
            results = [result for result, _ in self._items.values()]
            self._items.clear()
        for result in results:
            result.dispose()
