"""
RQ worker. Reads jobs from Redis and executes them in a separate process.

Start with:
    cd backend && source .venv/Scripts/activate && rq worker genomicsops --url redis://localhost:6379
"""
import os
from redis import Redis
from rq import Queue


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


def get_redis() -> Redis:
    return Redis.from_url(REDIS_URL)


def get_queue(name: str = "genomicsops") -> Queue:
    return Queue(name, connection=get_redis())


def enqueue(func, *args, **kwargs):
    q = get_queue()
    return q.enqueue(func, *args, **kwargs, job_timeout="1h", result_ttl=86400)
