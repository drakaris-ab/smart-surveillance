 
from pydantic import BaseModel
from datetime import datetime

class FaceReUserCreate(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None
    aadhaar: str | None = None
    criminal_flag: bool = False
    embedding: str

class FaceReUserResponse(FaceReUserCreate):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
