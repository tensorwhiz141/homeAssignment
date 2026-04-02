# database.py
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize client
_supabase: Client = None


def get_client() -> Client:
    """Lazy-initialize Supabase client."""
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[DB] Supabase keys missing — running without persistence")
            return None
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def generate_session_id() -> str:
    """Generate a unique session ID for each conversation."""
    return str(uuid.uuid4())


def save_message(session_id: str, role: str, message: str) -> bool:
    """
    Save a single conversation turn to Supabase.
    role: 'user' or 'assistant'
    """
    try:
        client = get_client()
        if not client:
            return False

        client.table("conversations").insert({
            "session_id": session_id,
            "role": role,
            "message": message
        }).execute()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_message: {e}")
        return False


def save_lead(session_id: str, extracted_data: dict, locked_language: str,
              eligible: bool = None, handoff_triggered: bool = False) -> bool:
    """
    Upsert lead data — updates if session exists, inserts if new.
    """
    try:
        client = get_client()
        if not client:
            return False

        record = {
            "session_id": session_id,
            "monthly_income": extracted_data.get("monthly_income"),
            "property_value": extracted_data.get("property_value"),
            "loan_amount_requested": extracted_data.get("loan_amount_requested"),
            "employment_status": extracted_data.get("employment_status"),
            "locked_language": locked_language,
            "eligible": eligible,
            "handoff_triggered": handoff_triggered
        }

        # Check if record exists
        existing = client.table("leads")\
            .select("id")\
            .eq("session_id", session_id)\
            .execute()

        if existing.data:
            # Update existing
            client.table("leads")\
                .update(record)\
                .eq("session_id", session_id)\
                .execute()
        else:
            # Insert new
            client.table("leads").insert(record).execute()

        return True
    except Exception as e:
        print(f"[DB ERROR] save_lead: {e}")
        return False


def save_handoff(session_id: str, lead_data: dict) -> bool:
    """
    Record a handoff event when user is routed to Human RM.
    """
    try:
        client = get_client()
        if not client:
            return False

        client.table("handoffs").insert({
            "session_id": session_id,
            "lead_data": lead_data
        }).execute()

        print(f"[HANDOFF SAVED] Session: {session_id}")
        return True
    except Exception as e:
        print(f"[DB ERROR] save_handoff: {e}")
        return False


def get_conversation_history(session_id: str) -> list:
    """
    Retrieve full conversation history for a session.
    Useful for resuming conversations.
    """
    try:
        client = get_client()
        if not client:
            return []

        result = client.table("conversations")\
            .select("role, message, created_at")\
            .eq("session_id", session_id)\
            .order("created_at")\
            .execute()

        return result.data or []
    except Exception as e:
        print(f"[DB ERROR] get_conversation_history: {e}")
        return []


def get_all_leads() -> list:
    """Retrieve all leads — useful for RM dashboard."""
    try:
        client = get_client()
        if not client:
            return []

        result = client.table("leads")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()

        return result.data or []
    except Exception as e:
        print(f"[DB ERROR] get_all_leads: {e}")
        return []