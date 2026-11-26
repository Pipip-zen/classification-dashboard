"""
Module: server/routes/inpainting.py
Deskripsi:
    Router FastAPI untuk Image Inpainting (pemulihan citra & penghapusan objek)
    menggunakan algoritma Telea dan Navier-Stokes.
"""

import cv2
import json
import base64
import numpy as np
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from core.inpainter import ImageInpainter
from server.auth import require_operator_role

router = APIRouter(
    prefix="/api/inpainting",
    tags=["Image Inpainting"],
    dependencies=[Depends(require_operator_role)],
)


@router.post("/inpaint")
async def inpaint_image(
    image_file: UploadFile = File(...),
    mask_file: Optional[UploadFile] = File(None),
    boxes_json: Optional[str] = Form(None),
    algorithm: str = Form("telea"),
    radius: int = Form(3)
):
    """Menghapus objek atau menyensor wilayah sensitif menggunakan inpainting."""
    try:
        # Baca gambar dasar
        img_bytes = await image_file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        base_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if base_img is None:
            raise HTTPException(status_code=400, detail="Gambar dasar tidak valid")

        h, w = base_img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        # Jika ada file mask yang diunggah
        if mask_file is not None:
            mask_bytes = await mask_file.read()
            marr = np.frombuffer(mask_bytes, np.uint8)
            decoded_mask = cv2.imdecode(marr, cv2.IMREAD_GRAYSCALE)
            if decoded_mask is not None:
                mask = cv2.resize(decoded_mask, (w, h))

        # Jika ada bounding box koordinat dari kanvas
        if boxes_json:
            try:
                boxes = json.loads(boxes_json)
                for b in boxes:
                    x1, y1, x2, y2 = [int(v) for v in b]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
            except Exception as e:
                print(f"[WARN] Gagal parse boxes_json: {e}")

        # Jalankan inpainting
        inpainter = ImageInpainter(method=algorithm, radius=radius)
        result_img = inpainter.inpaint(base_img, mask, method=algorithm, radius=radius)

        # Encode hasil
        _, buf = cv2.imencode('.jpg', result_img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        b64_str = base64.b64encode(buf).decode('utf-8')
        result_url = f"data:image/jpeg;base64,{b64_str}"

        return {
            "success": True,
            "algorithm": algorithm,
            "radius": radius,
            "resolution": {"width": w, "height": h},
            "result_url": result_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
