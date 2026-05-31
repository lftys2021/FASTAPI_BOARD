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
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, UniqueConstraint

from models import Post, User

import models
import schemas

from database import Base, engine
from database import SessionLocal

# password hashing 유틸 추가
from passlib.context import CryptContext

# 로그인 JWT 생성/검증 import 추가
from jose import JWTError, jwt
from datetime import datetime, timedelta

# 로그인 사용자 인증(Authentication)
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
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
@app.get(
    "/posts",
    response_model=list[schemas.PostResponse]
)
def get_posts(db: Session = Depends(get_db)):

    posts = db.query(models.Post).all()

    result = []

    for post in posts:
        result.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,

            "owner_id": post.owner_id,

            "author": {
                "id": post.owner.id,
                "username": post.owner.username
            },

            "created_at": post.created_at,
            "updated_at": post.updated_at,

            "likes_count": len(post.likes)
        })

    return result


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

# 게시글 생성
@app.post("/posts")
def create_post(post: schemas.PostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
#   db: Session = SessionLocal()

    new_post = models.Post(
        title=post.title,
        content=post.content,
        owner_id=current_user.id
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post


# 게시글 삭제
@app.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

#   db: Session = SessionLocal()

    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="게시글 없음"
        )

    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="삭제 권한 없음"
        )

    db.delete(post)
    db.commit()

    return {
        "message": "게시글 삭제 완료"
    }

# 게시글 수정
@app.put("/posts/{post_id}")
def update_post(
    post_id: int,
    updated_post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

#   db: Session = SessionLocal()

    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="게시글 없음"
        )
    
    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="수정 권한 없음"
        )

    post.title = updated_post.title
    post.content = updated_post.content
#    post.author = updated_post.author

    db.commit()
    db.refresh(post)

    return post

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



# 로그인 API 추가
@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User)\
        .filter(models.User.username == form_data.username)\
        .first()
    
    if db_user is None:
        raise HTTPException(status_code=401, detail="사용자 없음")
    
    valid_pw = verify_password(form_data.password, db_user.hashed_password)

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


# 실제로 인증이 되는지 확인
@app.get("/users/me")
def read_users_me(
    current_user = Depends(get_current_user)
):
    return current_user

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

# 좋아요 API
@app.post("/posts/{post_id}/like")
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="게시글 없음"
        )

    existing_like = db.query(models.Like)\
        .filter(
            models.Like.user_id == current_user.id,
            models.Like.post_id == post_id
        )\
        .first()

    if existing_like:
        raise HTTPException(
            status_code=400,
            detail="이미 좋아요를 눌렀습니다"
        )

    like = models.Like(
        user_id=current_user.id,
        post_id=post_id
    )

    db.add(like)
    db.commit()

    return {
        "message": "좋아요 완료"
    }

# 댓글 작성 API
@app.post(
    "/posts/{post_id}/comments",
    response_model=schemas.CommentResponse
)
def create_comment(
    post_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    post = db.query(models.Post)\
        .filter(models.Post.id == post_id)\
        .first()

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="게시글 없음"
        )

    new_comment = models.Comment(
        content=comment.content,
        post_id=post_id,
        owner_id=current_user.id
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return new_comment

# 댓글 목록 조회
@app.get(
    "/posts/{post_id}/comments",
    response_model=list[schemas.CommentResponse]
)
def get_comments(
    post_id: int,
    db: Session = Depends(get_db)
):

    return db.query(models.Comment)\
        .filter(models.Comment.post_id == post_id)\
        .all()

# 댓글 수정
@app.put(
    "/comments/{comment_id}",
    response_model=schemas.CommentResponse
)
def update_comment(
    comment_id: int,
    updated: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    comment = db.query(models.Comment)\
        .filter(models.Comment.id == comment_id)\
        .first()

    if comment is None:
        raise HTTPException(404, "댓글 없음")

    if comment.owner_id != current_user.id:
        raise HTTPException(403, "수정 권한 없음")

    comment.content = updated.content
    db.commit()
    db.refresh(comment)

    return comment

# 댓글 삭제
@app.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    comment = db.query(models.Comment)\
        .filter(models.Comment.id == comment_id)\
        .first()

    if comment is None:
        raise HTTPException(404, "댓글 없음")

    if comment.owner_id != current_user.id:
        raise HTTPException(403, "삭제 권한 없음")

    db.delete(comment)

    db.commit()

    return {
        "message": "댓글 삭제 완료"
    }