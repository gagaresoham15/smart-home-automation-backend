from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
try:
    from . import models, auth, database, schemas
    from .routers import admin, user, devices
except (ImportError, ValueError):
    import models, auth, database, schemas
    from routers import admin, user, devices
import datetime

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Smart Home Automation API")

# CORS middleware
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

app.include_router(admin.router)
app.include_router(user.router)
app.include_router(devices.router)

# Serve the frontend
@app.get("/")
# Route to serve uploads with manual CORS headers for maximum reliability
@app.get("/uploads/{filename}")
@app.head("/uploads/{filename}")
async def get_upload(filename: str):
    file_path = os.path.join("uploads", filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

# Mount CSS and JS directories
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user_obj = db.query(models.User).filter(
        (models.User.email == form_data.username) | (models.User.mobile == form_data.username)
    ).first()
    
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth.verify_password(form_data.password, user_obj.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user_obj.last_login = datetime.datetime.utcnow()
    db.commit()
    
    access_token = auth.create_access_token(
        data={"sub": user_obj.email if user_obj.email else user_obj.mobile, "role": user_obj.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Initialize default admin if not exists
@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    try:
        admin_email = "admin@smarthome.com"
        db_admin = db.query(models.User).filter(models.User.email == admin_email).first()
        if not db_admin:
            hashed_pwd = auth.get_password_hash("admin123")
            new_admin = models.User(
                full_name="System Admin",
                email=admin_email,
                mobile="0000000000",
                hashed_password=hashed_pwd,
                role=models.UserRole.ADMIN
            )
            db.add(new_admin)
            db.commit()
    finally:
        db.close()
