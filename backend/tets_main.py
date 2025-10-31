import pytest  
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from .main import app, get_session, AssignOrderRequest

client = TestClient(app)


def test_create_hero():
    client.get('/reset/')
    response = client.post(
        "/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["path"]
    assert data["robot_name"]
