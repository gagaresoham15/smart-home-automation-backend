from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
try:
    from .. import models, schemas, database
except (ImportError, ValueError):
    import models, schemas, database

router = APIRouter(
    prefix="/devices",
    tags=["esp32"]
)

@router.get("/{chip_id}/config")
def get_device_config(chip_id: str, db: Session = Depends(database.get_db)):
    device = db.query(models.Device).filter(models.Device.chip_id == chip_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    equipments = db.query(models.Equipment).filter(models.Equipment.chip_id == chip_id).all()
    return {
        "chip_id": chip_id,
        "is_assigned": device.is_assigned,
        "equipments": [
            {
                "id": eq.id,
                "name": eq.name,
                "gpio": eq.gpio_pin,
                "status": eq.status
            } for eq in equipments
        ]
    }

@router.post("/{chip_id}/status")
def update_device_status(chip_id: str, status_data: dict, db: Session = Depends(database.get_db)):
    # Simple heartbeat or status update from ESP32
    # In a real scenario, this might update a 'last_seen' timestamp
    return {"status": "received"}
