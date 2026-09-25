"""
Pure Python job runner. Polls the jobs table and executes queued jobs.
No Redis. No RQ. Works on Windows natively.

Run in a separate terminal:
    cd backend && source .venv/Scripts/activate && python -m app.jobs.runner
"""
import json
import sqlite3
import time
import traceback
from datetime import datetime, timezone
from app.config import settings


POLL_INTERVAL = 2  # seconds


def _conn():
    con = sqlite3.connect(settings.LOCAL_DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _claim_next_job():
    """Atomically claim the oldest queued job. Returns the job row or None."""
    con = _conn()
    try:
        # SQLite doesn't have SKIP LOCKED, so we use a transaction
        cur = con.execute(
            "SELECT * FROM jobs WHERE status = 'queued' "
            "ORDER BY created_at ASC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return None

        # Mark as running
        con.execute(
            "UPDATE jobs SET status = 'running', started_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), row["id"])
        )
        con.commit()
        return dict(row)
    finally:
        con.close()


def _finish_job(job_id: str, status: str, result=None, error=None):
    con = _conn()
    try:
        con.execute(
            "UPDATE jobs SET status = ?, result = ?, error = ?, finished_at = ? WHERE id = ?",
            (
                status,
                json.dumps(result) if result is not None else None,
                error,
                datetime.now(timezone.utc).isoformat(),
                job_id,
            )
        )
        con.commit()
    finally:
        con.close()


def _execute(job: dict):
    """Dispatch a job to its handler."""
    kind = job["kind"]
    args = json.loads(job.get("args") or "{}")

    # Import lazily so the runner doesn't need every dependency
    if kind == "process_vcf":
        from app.jobs.tasks import process_vcf_job
        process_vcf_job(
            job["id"],
            args["sample_id"],
            args["provider"],
            args["storage_path"],
        )
    elif kind == "annotate":
        from app.jobs.tasks import annotate_job
        annotate_job(job["id"], args["sample_id"])
    elif kind == "report":
        from app.jobs.tasks import report_job
        report_job(job["id"], job["user_id"], args["kind"], args["resource_id"])
    else:
        raise ValueError(f"Unknown job kind: {kind}")


def run_forever():
    print("=" * 60)
    print("  GenomicsOps job runner")
    print(f"  Polling every {POLL_INTERVAL}s. Ctrl+C to stop.")
    print("=" * 60)
    print()

    while True:
        try:
            job = _claim_next_job()
            if not job:
                time.sleep(POLL_INTERVAL)
                continue

            print(f"[JOB {job['id'][:8]}] {job['kind']} starting...")
            start = time.time()

            try:
                _execute(job)
                elapsed = time.time() - start
                # _execute internally updates the job status via _update_job
                # in tasks.py, so we just log here
                print(f"[JOB {job['id'][:8]}] {job['kind']} finished in {elapsed:.1f}s")
            except Exception as e:
                print(f"[JOB {job['id'][:8]}] FAILED: {e}")
                traceback.print_exc()
                _finish_job(job["id"], "failed", error=str(e))

        except KeyboardInterrupt:
            print()
            print("Runner stopped.")
            break
        except Exception as e:
            print(f"Runner error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_forever()
