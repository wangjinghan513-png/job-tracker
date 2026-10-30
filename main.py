from datetime import date
import hashlib
import secrets
from fastapi import Cookie, Response
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Literal

app = FastAPI()

# 数据库文件会保存在 main.py 所在的文件夹里
database_path = Path(__file__).parent / "applications.db"


def create_table():
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )


create_table()


class Application(BaseModel):
    company: str
    position: str
    status: Literal["已投递", "面试中", "已录用", "未通过"]
    applied_date: date | None = None

    @field_validator("company", "position")
    @classmethod
    def check_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("不能为空或仅包含空格")

        if len(value) > 100:
            raise ValueError("不能超过 100 个字符")

        return value


@app.get("/")
def home():
    return {"message": "我的求职管理系统启动成功！"}



@app.get("/applications")
def list_applications(
    status: str | None = None,
    session: str | None = Cookie(default=None),
):
    user = current_user(session)

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        if status:
            rows = connection.execute(
                """
                SELECT id, company, position, status, applied_date
                FROM applications
                WHERE user_id = ? AND status = ?
                """,
                (user["id"], status),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, company, position, status, applied_date
                FROM applications
                WHERE user_id = ?
                """,
                (user["id"],),
            ).fetchall()

    return [dict(row) for row in rows]


@app.post("/applications")
def create_application(
    application: Application,
    session: str | None = Cookie(default=None),
):
    user = current_user(session)

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
           INSERT INTO applications (company, position, status, user_id, applied_date)
VALUES (?, ?, ?, ?, ?)
""",            (
    application.company,
    application.position,
    application.status,
    user["id"],
    application.applied_date.isoformat() if application.applied_date else None,
), 
        )
        new_id = cursor.lastrowid

    return {"id": new_id, **application.model_dump()}


@app.put("/applications/{application_id}")
def update_application(
    application_id: int,
    application: Application,
    session: str | None = Cookie(default=None),
):
    user = current_user(session)

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE applications
            SET company = ?, position = ?, status = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                application.company,
                application.position,
                application.status,
                application_id,
                user["id"],
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")

    return {"id": application_id, **application.model_dump()}


@app.delete("/applications/{application_id}")
def delete_application(
    application_id: int,
    session: str | None = Cookie(default=None),
):
    user = current_user(session)

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM applications WHERE id = ? AND user_id = ?",
            (application_id, user["id"]),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")

    return {"message": "删除成功", "id": application_id}

      



@app.get("/page")
def show_page():
    from fastapi.responses import FileResponse

    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/music")
def play_music():
    from fastapi.responses import FileResponse

    return FileResponse(
        Path(__file__).parent / "music.mp4",
        media_type="video/mp4",
    )



from pydantic import Field
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def create_user_table():
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )


create_user_table()


class UserRegistration(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


@app.post("/register", status_code=201)
def register_user(user: UserRegistration):
    hashed_password = password_hash.hash(user.password)

    try:
        with sqlite3.connect(database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (user.username, hashed_password),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="用户名已存在")

    return {"id": user_id, "username": user.username}


@app.post("/login")
def login_user(user: UserRegistration, response: Response):
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (user.username,),
        ).fetchone()

    if row is None or not password_hash.verify(user.password, row[1]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成随机凭证，数据库中只保存它的哈希
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    import time
    expires_at = int(time.time()) + 60 * 60 * 24

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, row[0], expires_at),
        )

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )

    return {"message": "登录成功", "username": user.username}


import hashlib
import secrets

from fastapi import Cookie, Response


def create_session_table():
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )


create_session_table()


@app.post("/logout")
def logout_user(response: Response, session: str | None = Cookie(default=None)):
    if session:
        token_hash = hashlib.sha256(session.encode()).hexdigest()

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (token_hash,),
            )

    response.delete_cookie("session")
    return {"message": "已退出登录"}


@app.get("/me")
def current_user(session: str | None = Cookie(default=None)):
    if not session:
        raise HTTPException(status_code=401, detail="请先登录")

    import time

    token_hash = hashlib.sha256(session.encode()).hexdigest()

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username
            FROM sessions
            JOIN users ON sessions.user_id = users.id
            WHERE sessions.token_hash = ?
              AND sessions.expires_at > ?
            """,
            (token_hash, int(time.time())),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    return {"id": row[0], "username": row[1]}


def add_application_owner_column():
    with sqlite3.connect(database_path) as connection:
        columns = connection.execute(
            "PRAGMA table_info(applications)"
        ).fetchall()

        # 只有字段不存在时才添加，避免重复添加报错
        if not any(column[1] == "user_id" for column in columns):
            connection.execute(
                "ALTER TABLE applications ADD COLUMN user_id INTEGER"
            )


add_application_owner_column()


def add_application_date_column():
    with sqlite3.connect(database_path) as connection:
        columns = connection.execute(
            "PRAGMA table_info(applications)"
        ).fetchall()

        if not any(column[1] == "applied_date" for column in columns):
            connection.execute(
                "ALTER TABLE applications ADD COLUMN applied_date TEXT"
            )


add_application_date_column()

class ApplicationDateUpdate(BaseModel):
    applied_date: date | None


@app.patch("/applications/{application_id}/date")
def update_application_date(
    application_id: int,
    update: ApplicationDateUpdate,
    session: str | None = Cookie(default=None),
):
    user = current_user(session)

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE applications
            SET applied_date = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                update.applied_date.isoformat() if update.applied_date else None,
                application_id,
                user["id"],
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")

    return {"id": application_id, "applied_date": update.applied_date}
