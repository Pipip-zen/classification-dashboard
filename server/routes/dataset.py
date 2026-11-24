"""
Module: server/routes/dataset.py
Deskripsi:
    Router FastAPI untuk inspeksi dataset, taksonomi kelas taktis, dan ringkasan data training.
"""

import yaml
from pathlib import Path
from fastapi import APIRouter

from core.threat_evaluator import ThreatEvaluator

router = APIRouter(prefix="/api/dataset", tags=["Dataset & Taxonomy"])


@router.get("/taxonomy")
def get_taxonomy():
    """Mengambil daftar 8 taksonomi kelas taktis terpadu."""
    tax = ThreatEvaluator.TAXONOMY
    res = []
    for cid, info in tax.items():
        res.append({
            "class_id": cid,
            "name": info["name"],
            "display": info["display"],
            "domain": info["domain"],
            "threat": info["threat"],
            "threat_label": info["threat_label"],
            "color_hex": info["color_hex"],
            "ref_width_m": info.get("ref_width_m", 1.0),
            "allowed_modes": list(info.get("allowed_modes", []))
        })
    return {"classes": res, "total_classes": len(res)}


@router.get("/summary")
def get_dataset_summary():
    """Mengambil informasi ringkasan dataset dari data.yaml jika tersedia."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    yaml_path = base_dir / "data" / "unified_dataset" / "data.yaml"
    
    dataset_info = {
        "exists": False,
        "classes_count": 8,
        "train_samples": 0,
        "val_samples": 0,
        "classes_list": []
    }
    
    if yaml_path.exists():
        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
                names = data.get("names", [])
                dataset_info["exists"] = True
                dataset_info["classes_count"] = len(names)
                dataset_info["classes_list"] = names
                
                train_dir = base_dir / "data" / "unified_dataset" / "train" / "images"
                val_dir = base_dir / "data" / "unified_dataset" / "valid" / "images"
                if train_dir.exists():
                    dataset_info["train_samples"] = len(list(train_dir.glob("*.*")))
                if val_dir.exists():
                    dataset_info["val_samples"] = len(list(val_dir.glob("*.*")))
        except Exception as e:
            dataset_info["error"] = str(e)
            
    return dataset_info
