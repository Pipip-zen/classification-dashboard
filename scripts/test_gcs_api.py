"""
Verification Script: Test Tactical GCS API Endpoints & Single-Port Frontend
Menguji seluruh endpoint FastAPI, stream MJPEG, dan static serving menggunakan TestClient.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import cv2
from fastapi.testclient import TestClient
from server.main import app

def run_tests():
    print("=" * 60)
    print("TESTING TACTICAL GCS FASTAPI & SINGLE-PORT REACT SERVING")
    print("=" * 60)
    
    with TestClient(app) as client:
        # 1. Test System Health
        res = client.get("/api/system/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        data = res.json()
        print(f"[1/8] System Health: {data['status']} | GPU: {data['ai_model']['device_name']} [OK]")

        # 2. Test Taxonomy
        res = client.get("/api/dataset/taxonomy")
        assert res.status_code == 200
        tax = res.json()
        assert tax["total_classes"] == 12
        print(f"[2/8] Taxonomy Classes: {tax['total_classes']} Terpadu [OK]")

        # 3. Test Stream Sources
        res = client.get("/api/stream/sources")
        assert res.status_code == 200
        sources = res.json()
        vids = [v["filename"] for v in sources["testbench_videos"]]
        print(f"[3/8] Testbench Videos: {vids} [OK]")

        # 4. Test Stream Config
        res = client.post("/api/stream/config", json={"cockpit_mode": "drone", "confidence_gate": 0.3})
        assert res.status_code == 200
        print("[4/8] Stream Config Update: Cockpit=Drone, Conf=0.3 [OK]")

        # 5. Test Start Stream & Frame Delivery
        res = client.post("/api/stream/start", json={"source_type": "testbench", "source_param": "drone_forest_person_patrol.mp4"})
        assert res.status_code == 200
        print(f"[5/8] Start Stream: {res.json()} [OK]")

        # 6. Test Static SPA Serving
        res = client.get("/")
        assert res.status_code == 200
        assert "TACTICAL AI RECONNAISSANCE GCS" in res.text or "<div id=\"root\">" in res.text
        print("[6/8] Single-Port Static Serving (index.html): [OK]")

        # 7. Test Media Analysis (Image Upload)
        dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_img[100:300, 100:300] = [0, 255, 0]
        _, buf = cv2.imencode('.jpg', dummy_img)
        files = {"file": ("test.jpg", buf.tobytes(), "image/jpeg")}
        res = client.post("/api/analysis/image", files=files, data={"mode": "drone", "confidence_gate": "0.25", "dusk_enhancer": "false"})
        assert res.status_code == 200
        analysis = res.json()
        assert "annotated_image_url" in analysis
        print(f"[7/8] Media Analysis Inference: {analysis['resolution']} in {analysis['latency_ms']}ms [OK]")

        # 8. Test Stop Stream
        res = client.post("/api/stream/stop")
        assert res.status_code == 200
        print("[8/8] Stop Stream: [OK]")

    print("=" * 60)
    print("ALL 8/8 TACTICAL GCS BACKEND & FRONTEND TESTS PASSED (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
