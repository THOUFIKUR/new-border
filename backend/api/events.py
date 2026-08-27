"""BorderPulse — Events API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class EventAction(BaseModel):
    action: str  # acknowledge | resolve | false_positive


@router.get("/events")
async def list_events(limit: int = 50, status: Optional[str] = None):
    from backend.app import event_manager, db
    events = event_manager.get_all_events()
    if status:
        events = [e for e in events if e.status.value == status]
    events.sort(key=lambda e: e.started_at, reverse=True)
    return {
        "events": [e.to_dict() for e in events[:limit]],
        "total": len(events),
        "active_count": len(event_manager.get_active_events()),
        "today_count": event_manager.get_event_count_today(),
    }


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    from backend.app import event_manager, db
    event = event_manager.get_event(event_id)
    if not event:
        # Try Supabase
        if db:
            try:
                result = db.table("events").select("*").eq("id", event_id).execute()
                if result.data:
                    return {"event": result.data[0], "source": "supabase"}
            except Exception:
                pass
        raise HTTPException(status_code=404, detail="Event not found")
    return {"event": event.to_dict(), "source": "local"}


@router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventAction):
    from backend.app import event_manager
    action = body.action.lower()
    if action == "acknowledge":
        ok = event_manager.acknowledge_event(event_id)
    elif action == "resolve":
        ok = event_manager.resolve_event(event_id)
    elif action in ("false_positive", "false-positive"):
        ok = event_manager.mark_false_positive(event_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True, "event_id": event_id, "action": action}


@router.get("/events/{event_id}/media")
async def get_event_media(event_id: str):
    from backend.app import db
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        result = db.table("event_media").select("*").eq("event_id", event_id).execute()
        return {"media": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
