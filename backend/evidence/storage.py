"""
BorderPulse — Supabase Storage Upload
Uploads evidence snapshots and videos to Supabase Storage buckets.
On failure: retains local file and marks upload as FAILED for retry.
"""
import logging
import time
from pathlib import Path
from typing import Optional
import backend.config as cfg

logger = logging.getLogger("borderpulse.storage")

BUCKET_IMAGES = cfg.BUCKET_IMAGES
BUCKET_VIDEOS = cfg.BUCKET_VIDEOS


class StorageUploader:
    """
    Handles upload of evidence files to Supabase Storage.
    Gracefully handles failures — local evidence is always retained.
    """

    def __init__(self, supabase_client, db_client):
        self._storage = supabase_client.storage
        self._db = db_client

    def upload_snapshot(
        self,
        event_id: str,
        local_path: Path,
        camera_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Upload snapshot JPEG to event-images bucket. Returns media record or None."""
        if not local_path or not local_path.exists():
            logger.warning(f"Snapshot file missing: {local_path}")
            return None

        storage_path = f"{event_id}/snapshot.jpg"
        try:
            with open(local_path, "rb") as f:
                data = f.read()
            self._storage.from_(BUCKET_IMAGES).upload(
                storage_path, data,
                {"content-type": "image/jpeg", "upsert": "true"}
            )
            public_url = self._storage.from_(BUCKET_IMAGES).get_public_url(storage_path)

            # Insert media record
            row = {
                "event_id": event_id,
                "media_type": "snapshot",
                "storage_bucket": BUCKET_IMAGES,
                "storage_path": storage_path,
                "public_url": public_url,
                "mime_type": "image/jpeg",
                "file_size_bytes": local_path.stat().st_size,
                "metadata": {"camera_id": camera_id, "upload_status": "success"},
            }
            result = self._db.table("event_media").insert(row).execute()
            logger.info(f"Snapshot uploaded: {storage_path}")
            return result.data[0] if result.data else row

        except Exception as e:
            logger.error(f"Snapshot upload failed for event {event_id}: {e}")
            # Record failure in DB so it can be retried
            self._record_upload_failure(event_id, local_path, "snapshot", str(e))
            return None

    def upload_video(
        self,
        event_id: str,
        local_path: Path,
        camera_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Upload video clip to event-videos bucket."""
        if not local_path or not local_path.exists():
            logger.warning(f"Video file missing: {local_path}")
            return None

        storage_path = f"{event_id}/clip.mp4"
        try:
            with open(local_path, "rb") as f:
                data = f.read()
            self._storage.from_(BUCKET_VIDEOS).upload(
                storage_path, data,
                {"content-type": "video/mp4", "upsert": "true"}
            )
            file_size = local_path.stat().st_size

            row = {
                "event_id": event_id,
                "media_type": "video",
                "storage_bucket": BUCKET_VIDEOS,
                "storage_path": storage_path,
                "mime_type": "video/mp4",
                "file_size_bytes": file_size,
                "metadata": {"camera_id": camera_id, "upload_status": "success"},
            }
            result = self._db.table("event_media").insert(row).execute()
            logger.info(f"Video uploaded: {storage_path} ({file_size // 1024} KB)")
            return result.data[0] if result.data else row

        except Exception as e:
            logger.error(f"Video upload failed for event {event_id}: {e}")
            self._record_upload_failure(event_id, local_path, "video", str(e))
            return None

    def _record_upload_failure(self, event_id: str, local_path: Path,
                                media_type: str, error: str):
        """Record failed upload in DB for later retry. Local file is preserved."""
        try:
            row = {
                "event_id": event_id,
                "media_type": media_type,
                "storage_bucket": BUCKET_IMAGES if media_type == "snapshot" else BUCKET_VIDEOS,
                "storage_path": str(local_path),
                "mime_type": "image/jpeg" if media_type == "snapshot" else "video/mp4",
                "metadata": {
                    "upload_status": "FAILED",
                    "error": error,
                    "local_path": str(local_path),
                    "retry_pending": True,
                },
            }
            self._db.table("event_media").insert(row).execute()
        except Exception as db_err:
            logger.error(f"Could not record upload failure: {db_err}")
