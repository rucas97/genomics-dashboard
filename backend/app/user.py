"""
User abstraction.
In cloud mode, wraps a Supabase user. In local mode, wraps a local user row.
Both expose the same interface: .id, .email, .role.
"""
from dataclasses import dataclass


@dataclass
class CurrentUser:
    id: str
    email: str | None = None
    role: str = "analyst"  # cloud users default to analyst inside their org
    name: str | None = None
    is_local: bool = False


def from_supabase_user(sb_user) -> CurrentUser:
    """Wrap a Supabase auth user object."""
    return CurrentUser(
        id=str(sb_user.id),
        email=getattr(sb_user, "email", None),
        role="analyst",  # org role checked separately in cloud mode
        is_local=False,
    )


def from_local_user(row: dict) -> CurrentUser:
    """Wrap a SQLite user row."""
    return CurrentUser(
        id=row["id"],
        email=row.get("email"),
        role=row.get("role", "analyst"),
        name=row.get("name"),
        is_local=True,
    )
