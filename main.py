# from fastapi import FastAPI
from fastapi import FastAPI, Depends, HTTPException
# from pydantic import BaseModel

# app = FastAPI()

# # 게시글 저장소
# posts = []

# # 게시글 요청 데이터
# class PostCreate(BaseModel):
#     title: str
#     content: str
#     author: str
#     views: int


# # 루트
# @app.get("/")
# def root():
#     return {"message": "게시판 API"}


# # 게시글 목록 조회
# @app.get("/posts")
# def get_posts():
#     return posts


# # 게시글 생성
# @app.post("/posts")
# def create_post(post: PostCreate):

#     new_post = {
#         "id": len(posts) + 1,
#         "title": post.title,
#         "content": post.content,
#         "author": post.author,
#         "views": post.views
#     }

#     posts.append(new_post)

#     return new_post


# # 게시글 단일 조회
# @app.get("/posts/{post_id}")
# def get_post(post_id: int):

#     for post in posts:
#         if post["id"] == post_id:
#             views += 1
#             return post

#     return {"error": "게시글 없음"}


# # 게시글 삭제
# @app.delete("/posts/{post_id}")
# def delete_post(post_id: int):

#     for index, post in enumerate(posts):

#         if post["id"] == post_id:
#             deleted_post = posts.pop(index)

#             return {
#                 "message": "삭제 완료",
#                 "post": deleted_post
#             }

#     return {"error": "게시글 없음"}

# # 게시물 수정
# @app.put("/posts/{post_id}")
# def update_post(post_id: int, updated_post: PostCreate):

#     for post in posts:

#         if post["id"] == post_id:

#             post["title"] = updated_post.title
#             post["content"] = updated_post.content
#             post["author"] = updated_post.author

#             return {
#                 "message": "수정 완료",
#                 "post": post
#             }

#     return {"error": "게시글 없음"}

# main.py 전체 교체
from sqlalchemy.orm import Session

from models import Post, User

import models
import schemas

from database import engine
from database import SessionLocal

# password hashing 유틸 추가
from passlib.context import CryptContext

# 로그인 JWT 생성/검증 import 추가
from jose import JWTError, jwt
from datetime import datetime, timedelta

# 로그인 사용자 인증(Authentication)
from fastapi.security import OAuth2PasswordBearer
from fastapi import status
from jose import JWTError, jwt



app = FastAPI()

# 해시 설정 추가
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# JWT 설정 추가
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# DB 테이블 생성
models.Base.metadata.create_all(bind=engine)

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login"
)

# DB 세션 생성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 비밀번호 해시 함수 추가
def hash_password(password: str):

    return pwd_context.hash(password)

# 비밀번호 검증 함수 추가
def verify_password(plain_password, hashed_password):

    return pwd_context.verify(plain_password, hashed_password)

# 게시글 목록 조회
@app.get("/posts")
def get_posts(db: Session = Depends(get_db)):

#   db: Session = SessionLocal()

    posts = db.query(models.Post).all()

    return posts


# 게시글 상세 조회
@app.get("/posts/{post_id}", response_model=schemas.PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):

#   db: Session = SessionLocal()

    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        return {"error": "게시글 없음"}

    post.views += 1

    db.commit()
    db.refresh(post)

    return post

# 게시글 생성
@app.post("/posts")
def create_post(post: schemas.PostCreate, db: Session = Depends(get_db)):
    
#   db: Session = SessionLocal()

    new_post = models.Post(
        title=post.title,
        content= post.content,
        author=post.author
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


# 게시글 삭제
@app.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):

#   db: Session = SessionLocal()

    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        return {"error": "게시글 없음"}

    db.delete(post)

    db.commit()

    return {
        "message": "삭제 완료"
    }

# 게시글 수정
@app.put("/posts/{post_id}")
def update_post(post_id: int, updated_post: schemas.PostUpdate, db: Session = Depends(get_db)):

#   db: Session = SessionLocal()

    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        return {"error": "게시글 없음"}

    post.title = updated_post.title
    post.content = updated_post.content
    post.author = updated_post.author

    db.commit()

    db.refresh(post)

    return {
        "message": "수정 완료",
        "post": post
    }

# 의존성 주입(Depends)

# how to use response_model in FastAPI
# @app.get("/user", response_model=schemas.UserResponse)
# def get_user():
#     return {
#         "id": 1,
#         "name": "Alice",
#         "password": "1234"
#     }

# 회원가입 API 추가
@app.post("/signup",response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    hashed_pw = hash_password(user.password)

    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pw
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# JWT 생성 함수 추가
def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

# 현재 사용자 가져오기 함수
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception

    return user

# 로그인 API 추가
@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User)\
        .filter(models.User.username == user.username)\
        .first()
    
    if db_user is None:
        raise HTTPException(status_code=401, detail="사용자 없음")
    
    valid_pw = verify_password(user.password, db_user.hashed_password)

    if not valid_pw:
        raise HTTPException(status_code=401, detail="비밀번호 틀림")
    
    access_token = create_access_token(
        data={
            "sub": db_user.username
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# users 전체 조회
@app.get("/users", response_model=list[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users

# 특정 유저 조회
@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User)\
        .filter(models.User.id == user_id)\
        .first()

    if user is None:
        raise HTTPException(status_code=404, detail="사용자 없음")

    return user

# 회원 삭제 API 추가
@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):

    user = db.query(models.User)\
        .filter(models.User.id == user_id)\
        .first()

    if user is None:
        raise HTTPException(status_code=404, detail="사용자 없음")

    db.delete(user)
    db.commit()

    return {"message": "회원 삭제 완료"}

# 회원 수정 API 추가
@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, updated_user: schemas.UserUpdate, db: Session = Depends(get_db)):
    
    user = db.query(models.User)\
        .filter(models.User.id == user_id)\
        .first()
    
    if user is None:
        raise HTTPException(status_code=404, detail="사용자 없음")
    
    hashed_pw = hash_password(updated_user.password)

    user.username = updated_user.username
    user.email = updated_user.email
    user.hashed_password = hashed_pw

    db.commit()
    db.refresh(user)

    return user

# 보호된 API 만들기
@app.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user