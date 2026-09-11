# One writer, one connection, one transaction per batch.
#
# sqlite serialises writers, and it does it badly when asked to do it under
# contention: measured on a copy of production, the same write ran at 12k/s from
# one thread and 3k/s from 48, with the p99 going from 0.1ms to 79ms. Every
# thread that wants the lock is a thread sleeping on the busy handler, so the
# fastest shape is to stop competing for it. Requests hand a solve to this queue
# and return; this thread owns the connection and is the only thing that writes.
#
# Batching then comes for free, and it is where the rest of the win is. Fifty
# solves in one transaction pay for one commit instead of fifty, and because a
# batch usually holds repeats of the same (user, captcha) and the same
# five-minute cell, the tallies collapse into one "+n" apiece before they are
# written at all.
#
# The trade: a verify is acknowledged once the solve is queued, not once it is
# durable. A crash loses at most one batch window. That is deliberate, and it is
# the reason the solve path is a queue rather than a function call.
import logging
import queue
import sqlite3
import threading
import time
from collections import defaultdict

from services.rollup import bucket_of

log = logging.getLogger(__name__)

BATCH_MAX = 200  # solves per transaction
BATCH_WINDOW = 0.05  # seconds to wait for a batch to fill before writing
QUEUE_MAX = 50_000  # bounded: a wedged writer must show up as backpressure

_BUMP_COUNT = (
    "INSERT INTO solvecount (user_id, captcha_type, count) VALUES (?, ?, ?) "
    "ON CONFLICT (user_id, captcha_type) DO UPDATE SET count = count + excluded.count"
)
_BUMP_CELL = (
    "INSERT INTO solvebucket (bucket_start, user_id, captcha_type, count) VALUES (?, ?, ?, ?) "
    "ON CONFLICT (bucket_start, user_id, captcha_type) DO UPDATE SET count = count + excluded.count"
)
_INSERT_USER = "INSERT OR IGNORE INTO user (username) VALUES (?)"
_SELECT_USER = "SELECT id FROM user WHERE username = ?"


class SolveWriter:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.q: queue.Queue = queue.Queue(maxsize=QUEUE_MAX)
        self._conn: sqlite3.Connection | None = None
        self._user_ids: dict[str, int] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.dropped = 0

    # -- public ----------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="solve-writer", daemon=True)
        self._thread.start()

    def record(self, name: str, slug: str, solved_at: int | None = None) -> None:
        """Queue a solve. Returns immediately; never raises on a full queue."""
        try:
            self.q.put_nowait((name, slug, solved_at if solved_at is not None else int(time.time())))
        except queue.Full:
            # Losing a solve beats blocking the event loop behind a stuck writer.
            self.dropped += 1
            if self.dropped % 1000 == 1:
                log.warning("solve queue full, dropped %s solves", self.dropped)

    def stop(self, timeout: float = 5.0) -> None:
        """Flush what is queued and stop. Called on shutdown."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    # -- writer thread ---------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        # isolation_level=None hands transaction control back to us. Left at the
        # default, the driver opens one implicitly on the first write, and the
        # explicit BEGIN IMMEDIATE below then fails with "cannot start a
        # transaction within a transaction" -- which the batch retry swallows,
        # so every solve is silently lost.
        c = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA busy_timeout=30000")
        return c

    def _user_id(self, name: str) -> int:
        uid = self._user_ids.get(name)
        if uid is None:
            self._conn.execute(_INSERT_USER, (name,))
            uid = self._conn.execute(_SELECT_USER, (name,)).fetchone()[0]
            self._user_ids[name] = uid
        return uid

    def _drain(self) -> list:
        """One batch: block for the first item, then take what arrives quickly."""
        try:
            first = self.q.get(timeout=0.25)
        except queue.Empty:
            return []
        batch = [first]
        deadline = time.monotonic() + BATCH_WINDOW
        while len(batch) < BATCH_MAX:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                batch.append(self.q.get(timeout=remaining))
            except queue.Empty:
                break
        return batch

    def _write(self, batch: list) -> None:
        counts: dict[tuple[int, str], int] = defaultdict(int)
        cells: dict[tuple[int, int, str], int] = defaultdict(int)
        for name, slug, ts in batch:
            uid = self._user_id(name)
            counts[(uid, slug)] += 1
            cells[(bucket_of(ts), uid, slug)] += 1

        self._conn.execute("BEGIN IMMEDIATE")
        self._conn.executemany(_BUMP_COUNT, [(u, s, n) for (u, s), n in counts.items()])
        self._conn.executemany(_BUMP_CELL, [(b, u, s, n) for (b, u, s), n in cells.items()])
        self._conn.commit()

    def _run(self) -> None:
        self._conn = self._connect()
        while not (self._stop.is_set() and self.q.empty()):
            batch = self._drain()
            if not batch:
                continue
            try:
                self._write(batch)
            except Exception:
                # A failed batch is lost, but the writer has to survive it: the
                # alternative is a dead thread and a queue that fills forever.
                log.exception("solve batch of %s failed", len(batch))
                try:
                    self._conn.rollback()
                except Exception:
                    self._conn = self._connect()
        self._conn.close()


writer: SolveWriter | None = None


def init(db_path: str) -> SolveWriter:
    global writer
    if writer is None:
        writer = SolveWriter(db_path)
        writer.start()
    return writer


def record(name: str, slug: str) -> None:
    if writer is None:
        raise RuntimeError("solve writer not started; call init() at startup")
    writer.record(name, slug)
