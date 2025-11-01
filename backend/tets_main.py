import pytest  
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from .main import app, get_session, AssignOrderRequest

client = TestClient(app)


def test_assign_nearest_idle_robot():
    client.get('/reset/')
    response = client.post(
        "/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["path"]
    assert data["robot_name"]

def test_no_idle_robot_available():
    client.get('/reset/')
    # Assign all robots to make them busy
    client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})
    client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})

    # Now try to assign another robot
    response = client.post(
        "/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"}
    )
    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "No idle robot available"


