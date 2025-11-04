import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

from .main import app, get_session

# --- Create an in-memory database just for tests ---
TEST_DATABASE_URL = "sqlite://"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool, )


# --- Create tables only in the test engine ---
@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)  # optional cleanup


@pytest.fixture()
def session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture()
def client(session):
    # Override get_session to use the test session
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        c.get("/reset/")  # Reset the state before each test
        yield c
    app.dependency_overrides.clear()


def test_assign_nearest_idle_robot(client: TestClient, session: Session):
    response = client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})
    data = response.json()

    assert response.status_code == 200
    assert data["path"]
    assert data["robot_name"]


def test_no_idle_robot_available(client: TestClient, session: Session):
    # Assign all robots to make them busy
    client.post("/assignNearestIdleRobot/", json={"name": "O-1001", "source": "B"})
    client.post("/addOrder/", json={"name": "testOrder2", "source": "D", "target": "A"})
    client.post("/assignNearestIdleRobot/", json={"name": "testOrder2", "source": "D"})

    client.post("/addOrder/", json={"name": "testOrder3", "source": "A", "target": "E"})
    # Now try to assign another robot
    response = client.post("/assignNearestIdleRobot/", json={"name": "testOrder3", "source": "A"})
    data = response.json()

    assert response.status_code == 404
    assert data["detail"] == "No idle robot available"


def test_add_order(client: TestClient, session: Session):
    response = client.post("/addOrder/", json={"name": "testOrder", "source": "A", "target": "C"})
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == 1
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


def test_tick(client: TestClient, session: Session):
    request_body = {"name": "O-1001", "source": "B"}
    client.post("/assignNearestIdleRobot/", json=request_body)

    response = client.post("/tick/")

    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["note"] == "tick advanced (no-op stub)"


def test_routes(client: TestClient, session: Session):
    response = client.get("/routes/")
    data = response.json()

    assert response.status_code == 200
    assert data.__len__() == 1  # in the current db
