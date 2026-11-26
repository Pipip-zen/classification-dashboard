"""
Module: server/routes/stitching.py
Deskripsi:
    Router FastAPI untuk Image Stitching (Panorama generator) dari citra foto berurutan.
"""

import cv2
import base64
import numpy as np
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from core.stitcher import ImageStitcher
from server.auth import require_operator_role

router = APIRouter(
    prefix="/api/stitching",
    tags=["Image Stitching"],
    dependencies=[Depends(require_operator_role)],
)


@router.post("/stitch")
async def stitch_images(
    files: List[UploadFile] = File(...),
    mode: str = Form("panorama"),
    crop_borders: bool = Form(True)
):
    """Menggabungkan 2 atau lebih citra menjadi panorama."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Minimal 2 gambar diperlukan untuk proses stitching")

    loaded_images = []
    filenames = []
    
    for f in files:
        contents = await f.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            loaded_images.append(img)
            filenames.append(f.filename)

    if len(loaded_images) < 2:
        raise HTTPException(status_code=400, detail="Citra yang berhasil dibaca kurang dari 2")

    stitcher = ImageStitcher(mode=mode)
    success, panorama, msg = stitcher.stitch_images(loaded_images, crop_black_borders=crop_borders)

    if not success or panorama is None:
        return {
            "success": False,
            "message": msg,
            "panorama_url": None
        }

    h, w = panorama.shape[:2]
    _, buf = cv2.imencode('.jpg', panorama, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    b64_str = base64.b64encode(buf).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{b64_str}"

    return {
        "success": True,
        "message": msg,
        "input_images_count": len(loaded_images),
        "filenames": filenames,
        "resolution": {"width": w, "height": h},
        "panorama_url": data_url
    }
