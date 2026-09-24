"""
Safe Supabase helpers with retry-on-transient-error.
These live alongside the new abstraction layer so existing routers
keep working without changes.
"""
import time
import httpx
from app.supabase_client import supabase


TRANSIENT_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    ConnectionError,
)


def with_retry(fn, *args, retries: int = 3, delay: float = 0.3, **kwargs):
    last_exc = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except TRANSIENT_ERRORS as e:
            last_exc = e
            print(f"Transient DB error (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(delay * (attempt + 1))
    if last_exc:
        raise last_exc


def sb_select(table: str, columns: str = "*", filters: dict | None = None,
              order: str | None = None, desc: bool = False,
              limit: int | None = None):
    def _run():
        q = supabase.table(table).select(columns)
        if filters:
            for k, v in filters.items():
                q = q.eq(k, v)
        if order:
            q = q.order(order, desc=desc)
        if limit:
            q = q.limit(limit)
        return q.execute()
    return with_retry(_run)


def sb_insert(table: str, data):
    return with_retry(lambda: supabase.table(table).insert(data).execute())


def sb_update(table: str, data, filters: dict):
    def _run():
        q = supabase.table(table).update(data)
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute()
    return with_retry(_run)


def sb_delete(table: str, filters: dict):
    def _run():
        q = supabase.table(table).delete()
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute()
    return with_retry(_run)
