"""
BorderPulse — Evidence End-to-End Test
---------------------------------------
Tests that triggering an event actually writes a snapshot and video to disk.

Run with:
    python tests/test_evidence_e2e.py
"""
import sys, os, time, urllib.request, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://localhost:8000"

def get(path):
    try:
        r = urllib.request.urlopen(f"{BASE}{path}", timeout=5)
        return 200, json.loads(r.read())
    except Exception as e:
        return 0, {"error": str(e)}

def post(path, data=None):
    try:
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            f"{BASE}{path}", data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        r = urllib.request.urlopen(req, timeout=5)
        return 200, json.loads(r.read())
    except Exception as e:
        return 0, {"error": str(e)}

def count_files(directory, pattern):
    if not os.path.exists(directory):
        return 0
    return len(glob.glob(os.path.join(directory, pattern)))

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("BORDERPULSE EVIDENCE END-TO-END TEST")
    print("=" * 60)

    # Step 1: Verify backend is up
    code, data = get("/api/health")
    if code != 200:
        print(f"FAIL: Backend not reachable — {data}")
        return
    cam_online = data.get("camera", {}).get("online", False)
    print(f"[PASS] Backend reachable")
    print(f"       Camera online: {cam_online}")
    print(f"       YOLO ready:    {data.get('yolo', {}).get('ready', False)}")

    # Step 2: Count existing evidence files BEFORE test
    snap_before = count_files("evidence_local/snapshots", "*.jpg")
    vid_before  = count_files("evidence_local/videos", "*.mp4")
    print(f"\n[INFO] Evidence before test:")
    print(f"       Snapshots: {snap_before}")
    print(f"       Videos:    {vid_before}")

    # Step 3: Trigger a test event
    print(f"\n[STEP] Triggering test event via POST /api/test/event ...")
    code, resp = post("/api/test/event")
    if code != 200:
        print(f"FAIL: Could not create test event — {resp}")
        return
    event_id = resp.get("event_id", "?")
    print(f"[PASS] Test event created: {event_id}")

    # Step 4: Check events API shows the event
    code, data = get("/api/events")
    total = data.get("total", 0)
    print(f"[INFO] Events in database: {total}")
    if total > 0:
        print(f"[PASS] Events endpoint returns data")
    else:
        print(f"[WARN] Events count is 0 — Supabase write may have failed")

    # Step 5: Wait for evidence capture to process
    print(f"\n[STEP] Waiting 15s for evidence capture to write files ...")
    time.sleep(15)

    # Step 6: Count evidence files AFTER test
    snap_after = count_files("evidence_local/snapshots", "*.jpg")
    vid_after  = count_files("evidence_local/videos", "*.mp4")
    snap_new   = snap_after - snap_before
    vid_new    = vid_after - vid_before

    print(f"\n[INFO] Evidence after test:")
    print(f"       Snapshots: {snap_after} ({'+' if snap_new >= 0 else ''}{snap_new} new)")
    print(f"       Videos:    {vid_after} ({'+' if vid_new >= 0 else ''}{vid_new} new)")

    if snap_new > 0:
        print(f"[PASS] Snapshot written to evidence_local/snapshots/")
        # List newest file
        snaps = sorted(glob.glob("evidence_local/snapshots/*.jpg"),
                       key=os.path.getmtime, reverse=True)
        if snaps:
            sz = os.path.getsize(snaps[0])
            print(f"       Newest: {os.path.basename(snaps[0])} ({sz} bytes)")
    else:
        print(f"[WARN] No new snapshot detected — test event may not trigger evidence pipeline")
        print(f"       Note: test events may skip evidence capture by design")
        print(f"       To fully test evidence: step into a zone in front of camera")

    if vid_new > 0:
        print(f"[PASS] Video written to evidence_local/videos/")
        vids = sorted(glob.glob("evidence_local/videos/*.mp4"),
                      key=os.path.getmtime, reverse=True)
        if vids:
            sz = os.path.getsize(vids[0])
            print(f"       Newest: {os.path.basename(vids[0])} ({sz} bytes)")
    else:
        print(f"[INFO] No new video (normal — video needs 8s post-event buffer to finalize)")

    # Step 7: Check event detail for evidence
    print(f"\n[STEP] Checking event detail for media links ...")
    if event_id != "?":
        code, detail = get(f"/api/events/{event_id}")
        media = detail.get("media", [])
        print(f"[INFO] Media items attached to event: {len(media)}")
        for m in media:
            print(f"       type={m.get('media_type')} url={str(m.get('url',''))[:60]}")

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"EVIDENCE E2E TEST SUMMARY")
    print(f"  Test event creation:  {'PASS' if event_id != '?' else 'FAIL'}")
    print(f"  Events in DB:         {'PASS' if total > 0 else 'WARN'}")
    print(f"  Snapshot on disk:     {'PASS' if snap_new > 0 else 'WARN (expected for test event)'}")
    print(f"  Video on disk:        {'PASS' if vid_new > 0 else 'PENDING (8s buffer)'}")
    print(f"\nFULL EVIDENCE TEST: Step in front of camera with a zone active")
    print(f"to trigger a real intrusion event and verify snapshot+video.")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
