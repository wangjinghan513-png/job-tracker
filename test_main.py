import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    # 每次测试都使用临时数据库，不影响你的真实投递记录
    monkeypatch.setattr(main, "database_path", tmp_path / "test.db")
    main.create_table()
    with TestClient(main.app) as test_client:
        yield test_client


def test_create_and_list_application(client):
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


def test_reject_blank_company(client):
    response = client.post(
        "/applications",
        json={
            "company": "   ",
            "position": "实习生",
            "status": "已投递",
        },
    )

    assert response.status_code == 422


def test_reject_invalid_status(client):
    response = client.post(
        "/applications",
        json={
            "company": "测试公司",
            "position": "实习生",
            "status": "未知状态",
        },
    )

    assert response.status_code == 422


def test_update_missing_application(client):
    response = client.put(
        "/applications/999",
        json={
            "company": "测试公司",
            "position": "实习生",
            "status": "面试中",
        },
    )

    assert response.status_code == 404

def test_delete_application(client):
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


def test_filter_applications_by_status(client):
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

