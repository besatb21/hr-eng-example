import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from .main import app, get_session


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.close()

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    client = TestClient(app)
    yield client

def test_assign_nearest_idle_robot(client: TestClient, session: Session):
    response = client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})
    data = response.json()

    assert response.status_code == 200
    assert data["path"]
    assert data["robot_name"]


def test_no_idle_robot_available(client: TestClient):
    # Assign all robots to make them busy
    client.get('/reset/')
    client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})
    client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})

    # Now try to assign another robot
    response = client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})
    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "No idle robot available"


def test_add_order(client: TestClient):
    response = client.post("/addOrder/", json={"name": "testOrder", "source": "A", "target": "C"})
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 2
    assert data["name"] == "testOrder"
    assert data["source"] == "A"
    assert data["target"] == "C"
    assert data["status"] == "NEW"


def test_add_same_name_order(client: TestClient):
    client.post("/addOrder/", json={"name": "besa", "source": "A", "target": "C"})
    response = client.post("/addOrder/", json={"name": "besa", "source": "B", "target": "D"})
    data = response.json()

    assert response.status_code == 409
    assert data["detail"] == "Order with this name already exists"


def test_tick(client: TestClient):
    request_body = {
        "name": "O-1001",
        "source": "B"
    }

    client.post("/assignNearestIdleRobot/", json=request_body)

    response = client.post("/tick/")

    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["note"] == "tick advanced (no-op stub)"
