"""
Verification Script: Test Tactical GCS API Endpoints, RBAC Auth & Single-Port React
Menguji login 3 akun, otorisasi role-based, streaming dual-channel, dan static serving.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import cv2
from fastapi.testclient import TestClient
from server.main import app


def _login(client: TestClient, username: str, password: str) -> dict:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login gagal untuk {username}: {res.text}"
    data = res.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "token": data["access_token"],
        "user": data["user"],
    }


def run_tests():
    print("=" * 64)
    print("TESTING TACTICAL GCS FASTAPI, 3-ROLE AUTH RBAC & DUAL-CHANNEL")
    print("=" * 64)

    drone_user = os.getenv("DRONE_USERNAME", "drone")
    drone_pass = os.getenv("DRONE_PASSWORD", "drone123")
    rov_user = os.getenv("ROV_USERNAME", "rov")
    rov_pass = os.getenv("ROV_PASSWORD", "rov123")
    spec_user = os.getenv("SPECTATOR_USERNAME", "spectator")
    spec_pass = os.getenv("SPECTATOR_PASSWORD", "spectator123")

    with TestClient(app) as client:
        # 1. Public Health & Reject Unauthenticated
        res = client.get("/api/system/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        data = res.json()
        assert client.get("/api/channels/status").status_code == 401
        assert client.get("/api/dataset/taxonomy").status_code == 401
        print(f"[1/13] System Health & Unauth 401 Guard: {data['status']} | {data['ai_model']['device_name']} [OK]")

        # 2. Login 3 Akun & Tolak Password Salah
        bad_login = client.post("/api/auth/login", json={"username": drone_user, "password": "wrong"})
        assert bad_login.status_code == 401
        drone_auth = _login(client, drone_user, drone_pass)
        rov_auth = _login(client, rov_user, rov_pass)
        spec_auth = _login(client, spec_user, spec_pass)
        assert drone_auth["user"]["role"] == "drone"
        assert rov_auth["user"]["role"] == "rov"
        assert spec_auth["user"]["role"] == "spectator"
        print("[2/13] 3-Account Login (Admin Drone, Admin ROV, Spectator): [OK]")

        # 3. Strict RBAC Enforcement
        assert client.post("/api/channels/rov/start", json={"source_type": "testbench", "source_param": "rov_underwater_patrol.mp4"}, headers=drone_auth["headers"]).status_code == 403
        assert client.post("/api/channels/drone/start", json={"source_type": "testbench", "source_param": "drone_forest_person_patrol.mp4"}, headers=rov_auth["headers"]).status_code == 403
        assert client.get("/api/dataset/taxonomy", headers=spec_auth["headers"]).status_code == 403
        assert client.get("/api/analysis/samples", headers=spec_auth["headers"]).status_code == 403
        assert client.post("/api/channels/drone/config", json={"confidence_gate": 0.4}, headers=spec_auth["headers"]).status_code == 403
        assert client.post("/api/system/reload-model", headers=spec_auth["headers"]).status_code == 403

        spec_status = client.get("/api/channels/status", headers=spec_auth["headers"])
        assert spec_status.status_code == 200
        assert set(spec_status.json()["channels"].keys()) == {"drone", "rov"}

        drone_status = client.get("/api/channels/status", headers=drone_auth["headers"])
        assert set(drone_status.json()["channels"].keys()) == {"drone"}
        print("[3/13] Strict RBAC API Guards (Drone/ROV/Spectator Isolation): [OK]")

        # 4. Taxonomy & Sources (Operator Role)
        res = client.get("/api/dataset/taxonomy", headers=drone_auth["headers"])
        assert res.status_code == 200 and res.json()["total_classes"] == 8
        res = client.get("/api/stream/sources", headers=drone_auth["headers"])
        assert res.status_code == 200
        vids = [v["filename"] for v in res.json()["testbench_videos"]]
        print(f"[4/13] Taxonomy (8) & Testbench Sources: {vids} [OK]")

        # 5. Legacy Stream Config & Start (Admin Drone)
        res = client.post("/api/stream/config", json={"cockpit_mode": "drone", "confidence_gate": 0.3}, headers=drone_auth["headers"])
        assert res.status_code == 200
        res = client.post("/api/stream/start", json={"source_type": "testbench", "source_param": "drone_forest_person_patrol.mp4"}, headers=drone_auth["headers"])
        assert res.status_code == 200
        print("[5/13] Stream Config & Start (Admin Drone): [OK]")

        # 6. Single-Port SPA Serving
        res = client.get("/")
        assert res.status_code == 200 and "<div id=\"root\">" in res.text
        print("[6/13] Single-Port Static Serving (index.html): [OK]")

        # 7. Media Analysis (Image & Video)
        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_img[100:300, 100:300] = [0, 255, 0]
        _, buf = cv2.imencode(".jpg", dummy_img)
        files = {"file": ("test.jpg", buf.tobytes(), "image/jpeg")}
        res = client.post(
            "/api/analysis/image",
            files=files,
            data={"mode": "drone", "confidence_gate": "0.25", "dusk_enhancer": "false"},
            headers=drone_auth["headers"],
        )
        assert res.status_code == 200 and "annotated_image_url" in res.json()

        res_vid = client.post(
            "/api/analysis/video",
            data={"sample_filename": "drone_forest_person_patrol.mp4", "mode": "drone", "sampling_interval": "30"},
            headers=drone_auth["headers"],
        )
        assert res_vid.status_code == 200 and res_vid.json()["success"] is True
        print("[7/13] Media Analysis (Image & Video with Operator Auth): [OK]")

        # 8. Compass Calibration
        res_cal = client.post("/api/stream/compass/calibrate", json={"action": "set_north"}, headers=drone_auth["headers"])
        assert res_cal.status_code == 200 and res_cal.json()["heading_deg"] == 0.0
        res_off = client.post("/api/stream/compass/calibrate", json={"action": "set_offset", "offset_deg": 90.0}, headers=drone_auth["headers"])
        assert res_off.status_code == 200 and res_off.json()["cardinal"] == "E"
        print("[8/13] Compass Calibration: [OK]")

        # 9. Stop Stream
        assert client.post("/api/stream/stop", headers=drone_auth["headers"]).status_code == 200
        print("[9/13] Stop Stream: [OK]")

        # 10. Channel Lock, Conflict & PIN Takeover
        c1 = client.post("/api/channels/drone/claim", json={"session_id": "op-a"}, headers=drone_auth["headers"])
        assert c1.status_code == 200 and c1.json()["success"] is True
        c2 = client.post("/api/channels/drone/claim", json={"session_id": "op-b"}, headers=drone_auth["headers"])
        assert c2.status_code == 200 and c2.json()["locked"] is True
        c3 = client.post("/api/channels/drone/claim", json={"session_id": "op-b", "pin": "1234"}, headers=drone_auth["headers"])
        assert c3.status_code == 200 and c3.json()["success"] is True
        rel = client.post("/api/channels/drone/release", json={"session_id": "op-b"}, headers=drone_auth["headers"])
        assert rel.status_code == 200 and rel.json()["success"] is True
        print("[10/13] Channel Lock, Conflict & PIN Takeover: [OK]")

        # 11. Dual-Channel Concurrent Streaming (Admin Drone + Admin ROV + Spectator Verify)
        s_drone = client.post("/api/channels/drone/start", json={"source_type": "testbench", "source_param": "drone_forest_person_patrol.mp4"}, headers=drone_auth["headers"])
        s_rov = client.post("/api/channels/rov/start", json={"source_type": "testbench", "source_param": "rov_underwater_patrol.mp4"}, headers=rov_auth["headers"])
        assert s_drone.json()["success"] is True and s_rov.json()["success"] is True

        st_all = client.get("/api/channels/status", headers=spec_auth["headers"]).json()["channels"]
        assert st_all["drone"]["stream_active"] is True and st_all["rov"]["stream_active"] is True

        client.post("/api/channels/drone/stop", headers=drone_auth["headers"])
        client.post("/api/channels/rov/stop", headers=rov_auth["headers"])
        print("[11/13] Concurrent Admin Drone + Admin ROV + Spectator Sync: [OK]")

        # 12. WebSocket Unauthorized Rejections
        rejected = False
        try:
            with client.websocket_connect("/ws/ingest/drone") as ws_bad:
                ws_bad.receive_json()
        except Exception:
            rejected = True
        assert rejected, "Unauthenticated WebSocket ingest must be rejected"

        wrong_role_rejected = False
        try:
            with client.websocket_connect(f"/ws/ingest/drone?token={spec_auth['token']}") as ws_spec_in:
                ws_spec_in.receive_json()
        except Exception:
            wrong_role_rejected = True
        assert wrong_role_rejected, "Spectator must not connect to ingest WebSocket"
        print("[12/13] WebSocket RBAC Rejections (Unauth & Cross-Role): [OK]")

        # 13. WebSocket Authenticated Ingest (Drone) + Spectator View
        with client.websocket_connect(f"/ws/ingest/drone?token={drone_auth['token']}&session_id=ws-op-1&source_label=TestWindow") as ws_in:
            ready = ws_in.receive_json()
            assert ready["type"] == "ingest_ready"

            ws_in.send_bytes(buf.tobytes())
            tel_msg = ws_in.receive_json()
            assert tel_msg["type"] == "telemetry"
            assert tel_msg["telemetry"]["channel_id"] == "drone"

            with client.websocket_connect(f"/ws/view/drone?token={spec_auth['token']}&mode=main") as ws_view:
                frame_bytes = ws_view.receive_bytes()
                assert len(frame_bytes) > 100

        st_after = client.get("/api/channels/status", headers=spec_auth["headers"]).json()["channels"]["drone"]
        assert st_after["locked"] is False and st_after["stream_active"] is False
        print("[13/13] Authenticated WS Push Ingest + Spectator View + Auto-Unlock: [OK]")

    print("=" * 64)
    print("ALL 13/13 TACTICAL GCS AUTH & MULTI-CHANNEL TESTS PASSED (100%)")
    print("=" * 64)


if __name__ == "__main__":
    run_tests()
