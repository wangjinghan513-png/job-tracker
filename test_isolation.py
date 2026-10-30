import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def clients(tmp_path, monkeypatch):
    # 创建测试专用的临时数据库
    monkeypatch.setattr(main, "database_path", tmp_path / "test.db")
    main.create_table()
    main.add_application_owner_column()
    main.add_application_date_column()
    main.create_user_table()
    main.create_session_table()

    with TestClient(main.app) as first, TestClient(main.app) as second:
        yield first, second


def test_users_cannot_access_each_others_records(clients):
    first, second = clients

    # 注册并登录两个不同的测试账号
    for client, username in [(first, "user_one"), (second, "user_two")]:
        credentials = {
            "username": username,
            "password": "test-password-123",
        }
        assert client.post("/register", json=credentials).status_code == 201
        assert client.post("/login", json=credentials).status_code == 200

    record = {
        "company": "甲公司",
        "position": "实习生",
        "status": "已投递",
    }

    # 第一个用户创建一条记录
    response = first.post("/applications", json=record)
    assert response.status_code == 200
    record_id = response.json()["id"]

    # 第一个用户能看到，第二个用户看不到
    assert len(first.get("/applications").json()) == 1
    assert second.get("/applications").json() == []

    # 第二个用户不能修改或删除这条记录
    response = second.put(f"/applications/{record_id}", json=record)
    assert response.status_code == 404

    response = second.delete(f"/applications/{record_id}")
    assert response.status_code == 404

    # 原记录仍然存在
    assert len(first.get("/applications").json()) == 1


def test_logged_out_user_cannot_view_records(clients):
    first, _ = clients
    response = first.get("/applications")
    assert response.status_code == 401



def test_logged_out_user_cannot_change_records(clients):
    first, _ = clients

    record = {
        "company": "测试公司",
        "position": "实习生",
        "status": "已投递",
    }

    # 没有登录时，新增、修改、删除都应该被拒绝
    assert first.post("/applications", json=record).status_code == 401
    assert first.put("/applications/1", json=record).status_code == 401
    assert first.delete("/applications/1").status_code == 401


def test_user_cannot_change_another_users_date(clients):
    first, second = clients

    for client, username in [(first, "date_user_one"), (second, "date_user_two")]:
        credentials = {
            "username": username,
            "password": "test-password-123",
        }
        assert client.post("/register", json=credentials).status_code == 201
        assert client.post("/login", json=credentials).status_code == 200

    # 第一个用户创建记录
    response = first.post(
        "/applications",
        json={
            "company": "日期测试公司",
            "position": "实习生",
            "status": "已投递",
            "applied_date": "2026-10-30",
        },
    )
    assert response.status_code == 200
    record_id = response.json()["id"]

    # 第二个用户不能修改第一位用户的日期
    response = second.patch(
        f"/applications/{record_id}/date",
        json={"applied_date": "2026-11-01"},
    )
    assert response.status_code == 404

    # 第一位用户的原日期没有改变
    response = first.get("/applications")
    assert response.json()[0]["applied_date"] == "2026-10-30"
