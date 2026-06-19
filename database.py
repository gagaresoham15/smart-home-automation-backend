from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:lDsOuacgBCe1NoozLA0vtQLR0CZEeWRw@dpg-d8qjjobeo5us73co2cg0-a.oregon-postgres.render.com:5432/smart_home_ich0")

print(f"--- DATABASE CONNECTION: {SQLALCHEMY_DATABASE_URL} ---")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
