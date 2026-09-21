from app.supabase_client import supabase

def log_action(user_id, action, resource_type=None, resource_id=None, details=None):
    try:
        supabase.table("audit_log").insert({
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "details": details or {},
        }).execute()
    except Exception as e:
        print(f"audit log failed: {e}")
