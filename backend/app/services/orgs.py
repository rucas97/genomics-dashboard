"""
Organization and membership service.
Handles org lookup, role checks, invitations.
"""
import secrets
from datetime import datetime, timedelta
from app.supabase_client import supabase


def get_user_org(user_id: str) -> dict | None:
    """Return the user's active org, or None."""
    try:
        resp = supabase.table("org_members") \
            .select("*, organizations(*)") \
            .eq("user_id", user_id) \
            .eq("status", "active") \
            .limit(1) \
            .execute()
        if resp.data:
            return resp.data[0]
        return None
    except Exception as e:
        print(f"get_user_org failed: {e}")
        return None


def get_user_org_id(user_id: str) -> str | None:
    """Return just the org_id for convenience."""
    row = get_user_org(user_id)
    return row["org_id"] if row else None


def get_user_role(user_id: str) -> str | None:
    """Return the user's role in their org."""
    row = get_user_org(user_id)
    return row["role"] if row else None


def has_role(user_id: str, required: str) -> bool:
    """Check if user has at least the required role level."""
    role = get_user_role(user_id)
    ranks = {"owner": 4, "admin": 3, "analyst": 2, "viewer": 1}
    return ranks.get(role, 0) >= ranks.get(required, 0)


def list_members(org_id: str) -> list[dict]:
    """List all members of an org with their profile info."""
    try:
        resp = supabase.table("org_members") \
            .select("*, profiles(email, full_name)") \
            .eq("org_id", org_id) \
            .order("created_at") \
            .execute()
        return resp.data or []
    except Exception as e:
        print(f"list_members failed: {e}")
        return []


def create_invitation(org_id: str, email: str, role: str, invited_by: str) -> dict | None:
    """Create an invitation record and return it."""
    try:
        token = secrets.token_hex(32)
        expires = (datetime.utcnow() + timedelta(days=14)).isoformat()
        resp = supabase.table("org_invitations").upsert({
            "org_id": org_id,
            "email": email.lower(),
            "role": role,
            "token": token,
            "invited_by": invited_by,
            "expires_at": expires,
            "accepted_at": None,
        }, on_conflict="org_id,email").execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"create_invitation failed: {e}")
        return None


def list_invitations(org_id: str) -> list[dict]:
    try:
        resp = supabase.table("org_invitations") \
            .select("*") \
            .eq("org_id", org_id) \
            .is_("accepted_at", "null") \
            .order("created_at", desc=True) \
            .execute()
        return resp.data or []
    except Exception as e:
        print(f"list_invitations failed: {e}")
        return []


def revoke_invitation(invitation_id: str, org_id: str) -> bool:
    try:
        supabase.table("org_invitations") \
            .delete() \
            .eq("id", invitation_id) \
            .eq("org_id", org_id) \
            .execute()
        return True
    except Exception as e:
        print(f"revoke_invitation failed: {e}")
        return False


def accept_invitation(token: str, user_id: str) -> dict | None:
    """Accept an invitation by token. Adds the user to the org."""
    try:
        resp = supabase.table("org_invitations") \
            .select("*") \
            .eq("token", token) \
            .is_("accepted_at", "null") \
            .execute()
        if not resp.data:
            return None
        inv = resp.data[0]

        # Check expiry
        if inv.get("expires_at"):
            expires = datetime.fromisoformat(inv["expires_at"].replace("Z", "+00:00"))
            if expires < datetime.utcnow().replace(tzinfo=expires.tzinfo):
                return None

        # Add user to org
        supabase.table("org_members").upsert({
            "org_id": inv["org_id"],
            "user_id": user_id,
            "role": inv["role"],
            "status": "active",
            "invited_by": inv.get("invited_by"),
            "invited_at": inv.get("created_at"),
            "joined_at": datetime.utcnow().isoformat(),
        }, on_conflict="org_id,user_id").execute()

        # Mark invitation as accepted
        supabase.table("org_invitations") \
            .update({"accepted_at": datetime.utcnow().isoformat()}) \
            .eq("id", inv["id"]) \
            .execute()

        return inv
    except Exception as e:
        print(f"accept_invitation failed: {e}")
        return None


def update_member_role(org_id: str, user_id: str, new_role: str) -> bool:
    try:
        supabase.table("org_members") \
            .update({"role": new_role}) \
            .eq("org_id", org_id) \
            .eq("user_id", user_id) \
            .execute()
        return True
    except Exception as e:
        print(f"update_member_role failed: {e}")
        return False


def remove_member(org_id: str, user_id: str) -> bool:
    try:
        supabase.table("org_members") \
            .delete() \
            .eq("org_id", org_id) \
            .eq("user_id", user_id) \
            .execute()
        return True
    except Exception as e:
        print(f"remove_member failed: {e}")
        return False


def update_org_settings(org_id: str, patch: dict) -> bool:
    try:
        patch["updated_at"] = datetime.utcnow().isoformat()
        supabase.table("organizations").update(patch).eq("id", org_id).execute()
        return True
    except Exception as e:
        print(f"update_org_settings failed: {e}")
        return False
