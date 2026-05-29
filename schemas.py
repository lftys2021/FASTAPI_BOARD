from pydantic import BaseModel
from datetime import datetime

class PostCreate(BaseModel):
    title: str
    content: str
    author: str

class PostUpdate(BaseModel):
    title: str
    content: str
    author: str

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author: str
    views: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):

    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):

    username: str
    email: str
    password: str

class UserLogin(BaseModel):

    username: str
    password: str

class UserUpdate(BaseModel):

    username: str
    email: str
    password: str