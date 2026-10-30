import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    # 每次测试都使用临时数据库，不影响你的真实投递记录
    monkeypatch.setattr(main, "database_path", tmp_path / "test.db")
    main.create_table()
    main.add_application_owner_column()
    main.add_application_date_column()
    main.create_user_table()
    main.create_session_table()
    with TestClient(main.app) as test_client:
        yield test_client


def test_create_and_list_application(logged_in_client):
    client = logged_in_client
    response = client.post(
        "/applications",
        json={
            "company": "  测试公司  ",
            "position": "  实习生  ",
            "status": "已投递",
        },
    )

    assert response.status_code == 200
    assert response.json()["company"] == "测试公司"
    assert response.json()["position"] == "实习生"

    response = client.get("/applications")
    assert len(response.json()) == 1
    assert response.json()[0]["company"] == "测试公司"


def test_reject_blank_company(logged_in_client):
    client = logged_in_client
    response = client.post(
        "/applications",
        json={
            "company": "   ",
            "position": "实习生",
            "status": "已投递",
        },
    )

    assert response.status_code == 422


def test_reject_invalid_status(logged_in_client):
    client = logged_in_client
    response = client.post(
        "/applications",
        json={
            "company": "测试公司",
            "position": "实习生",
            "status": "未知状态",
        },
    )

    assert response.status_code == 422



def test_update_missing_application(logged_in_client):
    client = logged_in_client
    response = client.put(
        "/applications/999",
        json={
            "company": "测试公司",
            "position": "实习生",
            "status": "面试中",
        },
    )

    assert response.status_code == 404


def test_delete_application(logged_in_client):
    client = logged_in_client
  # 先创建一条测试记录
    response = client.post(
        "/applications",
        json={
            "company": "测试公司",
            "position": "实习生",
            "status": "已投递",
        },
    )
    application_id = response.json()["id"]

    # 删除刚创建的记录
    response = client.delete(f"/applications/{application_id}")
    assert response.status_code == 200

    # 再查询，确认记录已经不存在
    response = client.get("/applications")
    assert response.json() == []

    # 再次删除同一条记录，应该返回 404
    response = client.delete(f"/applications/{application_id}")
    assert response.status_code == 404


def test_filter_applications_by_status(logged_in_client):
    client = logged_in_client
    client.post(
        "/applications",
        json={
            "company": "甲公司",
            "position": "开发实习生",
            "status": "已投递",
        },
    )
    client.post(
        "/applications",
        json={
            "company": "乙公司",
            "position": "测试实习生",
            "status": "面试中",
        },
    )

    response = client.get(
        "/applications",
        params={"status": "面试中"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["company"] == "乙公司"


def test_update_application_status(logged_in_client):
    client = logged_in_client
    # 创建一条“已投递”的记录
    response = client.post(
        "/applications",
        json={
            "company": "测试公司",
            "position": "开发实习生",
            "status": "已投递",
        },
    )
    application_id = response.json()["id"]

    # 把状态改成“面试中”
    response = client.put(
        f"/applications/{application_id}",
        json={
            "company": "测试公司",
            "position": "开发实习生",
            "status": "面试中",
        },
    )

    assert response.status_code == 200

    # 重新查询，确认修改已保存
    response = client.get("/applications")
    assert response.json()[0]["status"] == "面试中"



def test_register_user(client):
    user = {
        "username": "test_user",
        "password": "test-password-123",
    }

    response = client.post("/register", json=user)

    assert response.status_code == 201
    assert response.json()["username"] == "test_user"
    assert "password" not in response.json()

    # 检查数据库里保存的是密码哈希
    with main.sqlite3.connect(main.database_path) as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            ("test_user",),
        ).fetchone()

    assert row is not None
    assert row[0] != user["password"]
    assert main.password_hash.verify(user["password"], row[0])

    # 相同用户名不能再次注册
    response = client.post("/register", json=user)
    assert response.status_code == 409


def test_login_user(client):
    # 先注册一个测试用户
    client.post(
        "/register",
        json={
            "username": "login_test",
            "password": "test-password-123",
        },
    )

    # 正确密码应该通过
    response = client.post(
        "/login",
        json={
            "username": "login_test",
            "password": "test-password-123",
        },
    )
    assert response.status_code == 200

    # 错误密码应该被拒绝
    response = client.post(
        "/login",
        json={
            "username": "login_test",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401

    # 不存在的用户也应该被拒绝
    response = client.post(
        "/login",
        json={
            "username": "unknown_user",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401

def test_login_and_logout_session(client):
    user = {
        "username": "session_test",
        "password": "test-password-123",
    }

    # 注册并登录
    assert client.post("/register", json=user).status_code == 201
    response = client.post("/login", json=user)

    assert response.status_code == 200
    assert client.cookies.get("session") is not None

    # 登录后，数据库里应该有一条会话记录
    with main.sqlite3.connect(main.database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]

    assert count == 1

    # 退出后，凭证和数据库记录都应被清除
    response = client.post("/logout")
    assert response.status_code == 200
    assert client.cookies.get("session") is None

    with main.sqlite3.connect(main.database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]

    assert count == 0



def test_current_user_requires_login(client):
    # 没有登录时不能查看当前用户
    response = client.get("/me")
    assert response.status_code == 401

    user = {
        "username": "me_test",
        "password": "test-password-123",
    }

    # 注册并登录
    assert client.post("/register", json=user).status_code == 201
    assert client.post("/login", json=user).status_code == 200

    # 登录后可以查看自己的用户名
    response = client.get("/me")
    assert response.status_code == 200
    assert response.json()["username"] == "me_test"

    # 退出后再次访问，会被拒绝
    assert client.post("/logout").status_code == 200
    assert client.get("/me").status_code == 401



@pytest.fixture
def logged_in_client(client):
    credentials = {
        "username": "application_test",
        "password": "test-password-123",
    }

    assert client.post("/register", json=credentials).status_code == 201
    assert client.post("/login", json=credentials).status_code == 200

    return client


def test_create_application_with_date(logged_in_client):
    response = logged_in_client.post(
        "/applications",
        json={
            "company": "日期测试公司",
            "position": "实习生",
            "status": "已投递",
            "applied_date": "2026-10-30",
        },
    )
    assert response.status_code == 200

    # 重新读取，确认日期已经保存
    response = logged_in_client.get("/applications")
    assert response.status_code == 200
    assert response.json()[0]["applied_date"] == "2026-10-30"


def test_update_application_date(logged_in_client):
    client = logged_in_client

    response = client.post(
        "/applications",
        json={
            "company": "日期测试公司",
            "position": "实习生",
            "status": "已投递",
        },
    )
    assert response.status_code == 200
    record_id = response.json()["id"]

    response = client.patch(
        f"/applications/{record_id}/date",
        json={"applied_date": "2026-10-30"},
    )
    assert response.status_code == 200

    response = client.get("/applications")
    assert response.json()[0]["applied_date"] == "2026-10-30"

