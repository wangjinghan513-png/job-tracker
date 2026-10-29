import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
    status: str


@app.get("/")
def home():
    return {"message": "我的求职管理系统启动成功！"}


@app.get("/applications")
def list_applications(status: str | None = None):
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        if status:
            rows = connection.execute(
                """
                SELECT id, company, position, status
                FROM applications
                WHERE status = ?
                """,
                (status,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, company, position, status FROM applications"
            ).fetchall()

    return [dict(row) for row in rows]


@app.post("/applications")
def create_application(application: Application):
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO applications (company, position, status)
            VALUES (?, ?, ?)
            """,
            (application.company, application.position, application.status),
        )
        new_id = cursor.lastrowid

    return {"id": new_id, **application.model_dump()}



@app.put("/applications/{application_id}")
def update_application(application_id: int, application: Application):
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE applications
            SET company = ?, position = ?, status = ?
            WHERE id = ?
            """,
            (
                application.company,
                application.position,
                application.status,
                application_id,
            ),
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="记录不存在")

    return {"id": application_id, **application.model_dump()}

@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM applications WHERE id = ?",
            (application_id,),
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


