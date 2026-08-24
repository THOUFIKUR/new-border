"""BorderPulse — Zones API (full CRUD)"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.vision.zones import Zone, ZonePoint

router = APIRouter()


class ZonePointModel(BaseModel):
    x: float
    y: float


class ZoneCreateModel(BaseModel):
    name: str
    polygon_points: List[ZonePointModel]
    camera_id: Optional[str] = None
    zone_type: str = "restricted"
    enabled: bool = True
    alert_on_classes: List[str] = ["person"]


class ZoneUpdateModel(BaseModel):
    name: Optional[str] = None
    polygon_points: Optional[List[ZonePointModel]] = None
    enabled: Optional[bool] = None
    alert_on_classes: Optional[List[str]] = None


@router.get("/zones")
async def list_zones():
    from backend.app import zone_engine
    return {"zones": zone_engine.to_frontend_list()}


@router.post("/zones", status_code=201)
async def create_zone(body: ZoneCreateModel):
    from backend.app import zone_engine, db
    import uuid

    if len(body.polygon_points) < 3:
        raise HTTPException(status_code=400, detail="Zone requires at least 3 points")

    zone_id = str(uuid.uuid4())
    pts = [ZonePoint(x=p.x, y=p.y) for p in body.polygon_points]
    zone = Zone(
        id=zone_id,
        name=body.name,
        camera_id=body.camera_id,
        polygon_points=pts,
        enabled=body.enabled,
        zone_type=body.zone_type,
        alert_on_classes=body.alert_on_classes,
    )
    zone_engine.add_zone(zone)

    # Persist to Supabase
    if db:
        try:
            row = {
                "id": zone_id,
                "name": body.name,
                "camera_id": body.camera_id,
                "zone_type": body.zone_type,
                "polygon_points": [{"x": p.x, "y": p.y} for p in body.polygon_points],
                "enabled": body.enabled,
                "alert_on_classes": body.alert_on_classes,
            }
            db.table("zones").insert(row).execute()
        except Exception as e:
            # Zone is still active locally even if DB write fails
            pass

    return {"zone": zone_engine.to_frontend_list()[-1], "id": zone_id}


@router.put("/zones/{zone_id}")
async def update_zone(zone_id: str, body: ZoneUpdateModel):
    from backend.app import zone_engine, db
    zones = {z.id: z for z in zone_engine.get_zones()}
    if zone_id not in zones:
        raise HTTPException(status_code=404, detail="Zone not found")

    zone = zones[zone_id]
    if body.name is not None:
        zone.name = body.name
    if body.polygon_points is not None:
        zone.polygon_points = [ZonePoint(x=p.x, y=p.y) for p in body.polygon_points]
    if body.enabled is not None:
        zone.enabled = body.enabled
    if body.alert_on_classes is not None:
        zone.alert_on_classes = body.alert_on_classes

    zone_engine.update_zone(zone)

    # Update in Supabase
    if db:
        try:
            update_data = {}
            if body.name: update_data["name"] = body.name
            if body.polygon_points: update_data["polygon_points"] = [{"x": p.x, "y": p.y} for p in body.polygon_points]
            if body.enabled is not None: update_data["enabled"] = body.enabled
            if body.alert_on_classes: update_data["alert_on_classes"] = body.alert_on_classes
            if update_data:
                db.table("zones").update(update_data).eq("id", zone_id).execute()
        except Exception:
            pass

    return {"success": True, "zone_id": zone_id}


@router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str):
    from backend.app import zone_engine, db
    zone_engine.remove_zone(zone_id)
    if db:
        try:
            db.table("zones").delete().eq("id", zone_id).execute()
        except Exception:
            pass
    return {"success": True, "zone_id": zone_id}


@router.post("/zones/{zone_id}/enable")
async def enable_zone(zone_id: str):
    from backend.app import zone_engine, db
    zones = {z.id: z for z in zone_engine.get_zones()}
    if zone_id not in zones:
        raise HTTPException(status_code=404, detail="Zone not found")
    zones[zone_id].enabled = True
    zone_engine.update_zone(zones[zone_id])
    if db:
        try:
            db.table("zones").update({"enabled": True}).eq("id", zone_id).execute()
        except Exception:
            pass
    return {"success": True, "zone_id": zone_id, "enabled": True}


@router.post("/zones/{zone_id}/disable")
async def disable_zone(zone_id: str):
    from backend.app import zone_engine, db
    zones = {z.id: z for z in zone_engine.get_zones()}
    if zone_id not in zones:
        raise HTTPException(status_code=404, detail="Zone not found")
    zones[zone_id].enabled = False
    zone_engine.update_zone(zones[zone_id])
    if db:
        try:
            db.table("zones").update({"enabled": False}).eq("id", zone_id).execute()
        except Exception:
            pass
    return {"success": True, "zone_id": zone_id, "enabled": False}
