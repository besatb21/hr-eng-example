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




def test_add_order():
    client.get('/reset/')
    response = client.post(
        "/addOrder/", json={"name": "testOrder", "source": "A", "target": "C"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"]== 2
    assert data["name"] == "testOrder"
    assert data["source"] == "A"
    assert data["target"] == "C"
    assert data["status"] == "NEW"


def test_add_same_name_order():
    client.get('/reset/')
    client.post(
        "/addOrder/", json={"name": "besa", "source": "A", "target": "C"}
    )
    response = client.post(
        "/addOrder/", json={"name": "besa", "source": "B", "target": "D"}
    )
    data = response.json()

    assert response.status_code == 409
    assert data["detail"] == "Order with this name already exists"

