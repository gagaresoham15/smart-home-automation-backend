from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
try:
    from .. import models, schemas, auth, database
except (ImportError, ValueError):
    import models, schemas, auth, database

from sqlalchemy import func
import datetime

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_admin_user)]
)

@router.get("/reports", response_model=schemas.AdminReportOut)
def get_reports(db: Session = Depends(database.get_db)):
    # Get last 6 months
    history = []
    today = datetime.datetime.utcnow()
    
    for i in range(5, -1, -1):
        # Calculate month and year
        month_date = today - datetime.timedelta(days=i*30)
        month_str = month_date.strftime("%b")
        year = month_date.year
        month_num = month_date.month
        
        # Count users registered in this month
        user_count = db.query(models.User).filter(
            func.extract('month', models.User.created_at) == month_num,
            func.extract('year', models.User.created_at) == year,
            models.User.role == models.UserRole.USER
        ).count()
        
        # Count devices registered in this month
        device_count = db.query(models.Device).filter(
            func.extract('month', models.Device.created_at) == month_num,
            func.extract('year', models.Device.created_at) == year
        ).count()
        
        history.append({
            "month": month_str,
            "users": user_count,
            "devices": device_count
        })
        
    return {"history": history}

@router.get("/stats", response_model=schemas.AdminDashboardStats)
def get_stats(db: Session = Depends(database.get_db)):
    total_users = db.query(models.User).filter(models.User.role == models.UserRole.USER).count()
    total_devices = db.query(models.Device).count()
    unassigned_devices = db.query(models.Device).filter(models.Device.is_assigned == False).count()
    assigned_devices = total_devices - unassigned_devices
    
    return {
        "total_users": total_users,
        "total_devices": total_devices,
        "unassigned_devices": unassigned_devices,
        "assigned_devices": assigned_devices
    }

@router.post("/devices", response_model=schemas.DeviceOut)
def register_device(device: schemas.DeviceCreate, db: Session = Depends(database.get_db)):
    db_device = db.query(models.Device).filter(models.Device.chip_id == device.chip_id).first()
    if db_device:
        raise HTTPException(status_code=400, detail="Device already registered")
    
    new_device = models.Device(chip_id=device.chip_id)
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.post("/devices/upload")
async def upload_devices(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    
    if "chip_id" not in df.columns:
        raise HTTPException(status_code=400, detail="Excel file must contain a 'chip_id' column.")
    
    chip_ids = df["chip_id"].astype(str).tolist()
    added_count = 0
    skipped_count = 0
    
    for cid in chip_ids:
        db_device = db.query(models.Device).filter(models.Device.chip_id == cid).first()
        if not db_device:
            new_device = models.Device(chip_id=cid)
            db.add(new_device)
            added_count += 1
        else:
            skipped_count += 1
            
    db.commit()
    return {"message": f"Successfully added {added_count} devices. Skipped {skipped_count} existing devices."}

@router.get("/devices", response_model=List[schemas.DeviceOut])
def list_devices(db: Session = Depends(database.get_db)):
    return db.query(models.Device).all()

@router.get("/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(database.get_db)):
    return db.query(models.User).filter(models.User.role == models.UserRole.USER).all()

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Unassign devices first if any
    assignments = db.query(models.DeviceAssignment).filter(models.DeviceAssignment.user_id == user_id).all()
    for auth_ass in assignments:
        device = db.query(models.Device).filter(models.Device.chip_id == auth_ass.chip_id).first()
        if device:
            device.is_assigned = False
    
    db.query(models.DeviceAssignment).filter(models.DeviceAssignment.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.delete("/devices/{chip_id}")
def delete_device(chip_id: str, db: Session = Depends(database.get_db)):
    device = db.query(models.Device).filter(models.Device.chip_id == chip_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.query(models.Equipment).filter(models.Equipment.chip_id == chip_id).delete()
    db.query(models.DeviceAssignment).filter(models.DeviceAssignment.chip_id == chip_id).delete()
    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}
