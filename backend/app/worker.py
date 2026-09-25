"""
Job queue abstraction. Currently uses a DB-polling runner (jobs/runner.py).
Kept as a module so the interface stays stable if we move to Redis/RQ later.
"""

def enqueue(func, *args, **kwargs):
    """Deprecated. Jobs are now created directly in the jobs table."""
    raise NotImplementedError(
        "enqueue() is deprecated. Use the /jobs endpoints to create jobs, "
        "and run `python -m app.jobs.runner` to process them."
    )
