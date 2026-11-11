"""
HS AI SOLUTIONS — AUTONOMOUS SCHEDULING & AUTOMATION ENGINE
Module: hs_ecosystem.agent.scheduler
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 10:
- Cron and interval scheduling engine
- SQLite persistence across daemon restarts
- File-watcher triggers
- Webhook triggers
- Autonomous execution of recurring agent goals
"""

from __future__ import annotations
import os
import sys
import time
import json
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
import croniter


@dataclass
class ScheduledJob:
    id: str
    name: str
    cron_expr: Optional[str]
    interval_seconds: Optional[float]
    goal: str
    is_active: bool = True
    last_run_at: Optional[float] = None
    next_run_at: Optional[float] = None
    run_count: int = 0
    created_at: float = field(default_factory=time.time)


class PersistentSchedulerStore:
    """SQLite-backed store for scheduled jobs."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path.cwd() / "hs_ecosystem" / "storage" / "agent_scheduler.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cron_expr TEXT,
                interval_seconds REAL,
                goal TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_run_at REAL,
                next_run_at REAL,
                run_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            );
            """)
            conn.commit()

    def save_job(self, job: ScheduledJob):
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO scheduled_jobs
            (id, name, cron_expr, interval_seconds, goal, is_active, last_run_at, next_run_at, run_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.name, job.cron_expr, job.interval_seconds, job.goal,
                1 if job.is_active else 0, job.last_run_at, job.next_run_at, job.run_count, job.created_at
            ))
            conn.commit()

    def load_jobs(self) -> List[ScheduledJob]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM scheduled_jobs WHERE is_active = 1")
            jobs = []
            for r in cur.fetchall():
                jobs.append(ScheduledJob(
                    id=r["id"],
                    name=r["name"],
                    cron_expr=r["cron_expr"],
                    interval_seconds=r["interval_seconds"],
                    goal=r["goal"],
                    is_active=bool(r["is_active"]),
                    last_run_at=r["last_run_at"],
                    next_run_at=r["next_run_at"],
                    run_count=r["run_count"],
                    created_at=r["created_at"]
                ))
            return jobs

    def delete_job(self, job_id: str) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cur.rowcount > 0


class AutonomousScheduler:
    """Runs scheduled jobs in the background, executing goals via callback."""

    def __init__(self, store: Optional[PersistentSchedulerStore] = None, executor_callback: Optional[Callable[[str], Any]] = None):
        self.store = store or PersistentSchedulerStore()
        self.executor_callback = executor_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_cron_job(self, name: str, cron_expr: str, goal: str) -> ScheduledJob:
        base_time = time.time()
        c = croniter.croniter(cron_expr, base_time)
        next_run = c.get_next()

        import uuid
        job = ScheduledJob(
            id=f"job_{uuid.uuid4().hex[:8]}",
            name=name,
            cron_expr=cron_expr,
            interval_seconds=None,
            goal=goal,
            next_run_at=next_run
        )
        self.store.save_job(job)
        return job

    def add_interval_job(self, name: str, interval_seconds: float, goal: str) -> ScheduledJob:
        import uuid
        job = ScheduledJob(
            id=f"job_{uuid.uuid4().hex[:8]}",
            name=name,
            cron_expr=None,
            interval_seconds=interval_seconds,
            goal=goal,
            next_run_at=time.time() + interval_seconds
        )
        self.store.save_job(job)
        return job

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [job.__dict__ for job in self.store.load_jobs()]

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self):
        while self._running:
            now = time.time()
            jobs = self.store.load_jobs()
            for j in jobs:
                if j.next_run_at and now >= j.next_run_at:
                    # Trigger job
                    j.last_run_at = now
                    j.run_count += 1

                    # Recalculate next run
                    if j.cron_expr:
                        c = croniter.croniter(j.cron_expr, now)
                        j.next_run_at = c.get_next()
                    elif j.interval_seconds:
                        j.next_run_at = now + j.interval_seconds

                    self.store.save_job(j)

                    if self.executor_callback:
                        threading.Thread(target=self.executor_callback, args=(j.goal,), daemon=True).start()

            time.sleep(1.0)
