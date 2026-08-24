"""
BorderPulse — Supabase Client Wrapper
Initializes both anon (frontend/read) and service-role (backend/write) clients.
Service-role key NEVER leaves this module or the backend process.
"""
import logging
from typing import Optional
from supabase import create_client, Client
import backend.config as cfg

logger = logging.getLogger("borderpulse.database")

_service_client: Optional[Client] = None
_anon_client: Optional[Client] = None


def get_service_client() -> Optional[Client]:
    """Backend-only service-role client. Full table access, bypasses RLS."""
    global _service_client
    if _service_client:
        return _service_client
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Supabase URL or SERVICE_ROLE_KEY not configured")
        return None
    if cfg.SUPABASE_SERVICE_ROLE_KEY.startswith("REPLACE_"):
        logger.warning("Supabase SERVICE_ROLE_KEY is a placeholder — DB writes disabled")
        return None
    try:
        _service_client = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase service client connected")
        return _service_client
    except Exception as e:
        logger.error(f"Supabase service client init failed: {e}")
        return None


def get_anon_client() -> Optional[Client]:
    """Anon client — safe for read operations where RLS allows anonymous access."""
    global _anon_client
    if _anon_client:
        return _anon_client
    if not cfg.SUPABASE_URL or not cfg.SUPABASE_PUBLISHABLE_KEY:
        return None
    try:
        _anon_client = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_PUBLISHABLE_KEY)
        return _anon_client
    except Exception as e:
        logger.error(f"Supabase anon client init failed: {e}")
        return None


def check_supabase_connection() -> bool:
    """Health check — verify Supabase is reachable."""
    client = get_service_client()
    if not client:
        client = get_anon_client()
    if not client:
        return False
    try:
        result = client.table("system_settings").select("key").limit(1).execute()
        return result.data is not None
    except Exception as e:
        logger.error(f"Supabase connection check failed: {e}")
        return False
