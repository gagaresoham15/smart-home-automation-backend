
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
import shutil
import os
import uuid
try:
    from .. import models, schemas, auth, database
except (ImportError, ValueError):
    import models, schemas, auth, database

router = APIRouter(
    prefix="/user",
    tags=["user"]
)

@router.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_mobile = db.query(models.User).filter(models.User.mobile == user.mobile).first()
    if db_mobile:
        raise HTTPException(status_code=400, detail="Mobile number already registered")
    
    hashed_pwd = auth.get_password_hash(user.password)
    new_user = models.User(
        full_name=user.full_name,
        email=user.email,
        mobile=user.mobile,
        hashed_password=hashed_pwd,
        role=models.UserRole.USER
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/claim-device")
def claim_device(device_id: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    device = db.query(models.Device).filter(models.Device.chip_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device ID not found in system")
    
    if device.is_assigned:
        raise HTTPException(status_code=400, detail="Device is already assigned to a user")
    
    assignment = models.DeviceAssignment(user_id=current_user.id, chip_id=device_id)
    device.is_assigned = True
    
    db.add(assignment)
    db.commit()
    return {"message": f"Device {device_id} successfully assigned to you"}

@router.get("/my-devices", response_model=List[schemas.DeviceOut])
def get_my_devices(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Device).join(models.DeviceAssignment).filter(models.DeviceAssignment.user_id == current_user.id).all()

@router.post("/equipment", response_model=schemas.EquipmentOut)
def add_equipment(equipment: schemas.EquipmentCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Verify device ownership
    assignment = db.query(models.DeviceAssignment).filter(
        models.DeviceAssignment.chip_id == equipment.chip_id,
        models.DeviceAssignment.user_id == current_user.id
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=403, detail="You do not own this device")
    
    new_equipment = models.Equipment(
        chip_id=equipment.chip_id,
        name=equipment.name,
        room_name=equipment.room_name,
        gpio_pin=equipment.gpio_pin
    )
    db.add(new_equipment)
    db.commit()
    db.refresh(new_equipment)
    return new_equipment

@router.get("/equipment", response_model=List[schemas.EquipmentOut])
def list_equipment(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Equipment).join(
        models.DeviceAssignment, 
        models.Equipment.chip_id == models.DeviceAssignment.chip_id
    ).filter(models.DeviceAssignment.user_id == current_user.id).all()

@router.post("/equipment/{equipment_id}/toggle")
def toggle_equipment(equipment_id: int, status: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    equipment = db.query(models.Equipment).join(
        models.DeviceAssignment,
        models.Equipment.chip_id == models.DeviceAssignment.chip_id
    ).filter(
        models.Equipment.id == equipment_id,
        models.DeviceAssignment.user_id == current_user.id
    ).first()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found or not owned by you")
    
    if status not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Status must be ON or OFF")
        
    equipment.status = status
    db.commit()
    return {"status": equipment.status}

@router.delete("/equipment/{equipment_id}")
def delete_equipment(equipment_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    equipment = db.query(models.Equipment).join(
        models.DeviceAssignment,
        models.Equipment.chip_id == models.DeviceAssignment.chip_id
    ).filter(
        models.Equipment.id == equipment_id,
        models.DeviceAssignment.user_id == current_user.id
    ).first()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found or not owned by you")
    
    db.delete(equipment)
    db.commit()
    return {"message": "Equipment deleted successfully"}

@router.delete("/room/{room_name}")
def delete_room(room_name: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    import urllib.parse
    # Decode the room name from URL encoding
    decoded_name = urllib.parse.unquote(room_name).strip()
    
    # Find all equipment in this room owned by the user (case-insensitive)
    from sqlalchemy import func
    equipments = db.query(models.Equipment).join(
        models.DeviceAssignment,
        models.Equipment.chip_id == models.DeviceAssignment.chip_id
    ).filter(
        func.lower(models.Equipment.room_name) == func.lower(decoded_name),
        models.DeviceAssignment.user_id == current_user.id
    ).all()
    
    if not equipments:
        # If no equipment is found, we still return success. 
        # This handles UI-only room labels that haven't had equipment assigned yet.
        return {"message": f"Room '{decoded_name}' removed from your view"}
    
    for eq in equipments:
        db.delete(eq)
        
    db.commit()
    return {"message": f"Room '{decoded_name}' and its equipment deleted successfully"}
@router.put("/profile", response_model=schemas.UserOut)
def update_profile(user_update: schemas.UserCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Check if new mobile is already taken by someone else
    if user_update.mobile != current_user.mobile:
        db_mobile = db.query(models.User).filter(models.User.mobile == user_update.mobile).first()
        if db_mobile:
            raise HTTPException(status_code=400, detail="Mobile number already registered by another user")
    
    current_user.full_name = user_update.full_name
    current_user.mobile = user_update.mobile
    # We can also handle password update if needed, but let's keep it simple for now
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/profile-image")
async def upload_profile_image(file: UploadFile = File(...), db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    if file_extension.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, GIF, and WEBP allowed.")
    
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("uploads", new_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update user model
    # Delete old image if exists
    if current_user.profile_image:
        old_path = current_user.profile_image.lstrip('/')
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except:
                pass
                
    current_user.profile_image = f"/uploads/{new_filename}"
    db.commit()
    
    return {"profile_image": current_user.profile_image}

@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user
