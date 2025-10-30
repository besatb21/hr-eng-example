from enum import Enum
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# -----------------------------
# Persistence With SQLite Setup
# -----------------------------


from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select


class RobotStatus(str, Enum):
    IDLE = "IDLE"
    EXECUTING = "EXECUTING"

class OrderStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"


class Robot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    status: RobotStatus
    node: str

class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    source: str
    target: str
    status: OrderStatus=OrderStatus.NEW


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

# todo
SessionDep = Annotated[Session, Depends(get_session)]


# -----------------------------
# Domain Models (Pydantic)
# -----------------------------
class Edge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    weight: float = 1.0

    class Config:
        allow_population_by_field_name = True
        json_encoders = {RobotStatus: lambda s: s.value, OrderStatus: lambda s: s.value}

class Graph(BaseModel):
    nodes: List[str]
    edges: List[Edge]

# -----------------------------
# API Schemas
# -----------------------------

class AddOrderRequest(BaseModel):
    name: str
    source: str
    target: str

class RetrieveOrderRequest(BaseModel):
    id: int
    name: str
    source: str
    target: str

    class Config:
        from_attributes = True


class RetrieveRobotRequest(BaseModel):
    id: int
    name: str
    status: RobotStatus
    node: str

    class Config:
        from_attributes = True


# -----------------------------
# In-memory State (Replace with DB for prod)
# -----------------------------


GRAPH: Graph = Graph(
    nodes=["A", "B", "C", "D", "E", "F"],
    edges=[
        Edge(**{"from_": "A", "to": "B", "weight": 1}),
        Edge(**{"from_": "B", "to": "C", "weight": 2}),
        Edge(**{"from_": "C", "to": "D", "weight": 2}),
        Edge(**{"from_": "B", "to": "E", "weight": 3}),
        Edge(**{"from_": "E", "to": "F", "weight": 1}),
        Edge(**{"from_": "D", "to": "F", "weight": 2}),
        # Treat edges as undirected for simplicity; callers may add both directions explicitly if desired
    ],
)

SEED_ROBOTS = [
    Robot(name="R1", status=RobotStatus.IDLE, node="A"),
    Robot(name="R2", status=RobotStatus.EXECUTING, node="C"),
    Robot(name="R3", status=RobotStatus.IDLE, node="E"),
]

SEED_ORDERS = [
    Order(name="O-1001", source="B", target="D", status=OrderStatus.NEW),
]

# -----------------------------
# App Setup
# -----------------------------

app = FastAPI(
    title="AGV Scheduling Exercise API",
    version="0.1.0",
    description=(
        "Minimal backend stubs for the AGV fleet scheduling exercise.\n\n"
        "Endpoints provided: /addOrder, /getOrders, /getGraph, /getRobots.\n"
        "State is in-memory and resets on restart."
    ),
)

# CORS for local dev frontends (Vite/Next/CRA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # CRA/Next.js
        "*",  # loosen for exercise; tighten for prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------

def _graph_nodes_set() -> set:
    return set(GRAPH.nodes)


def seed_data(session: Session):
    """Insert sample data if the table is empty."""
    orders = SEED_ORDERS
    robots = SEED_ROBOTS
    session.add_all(orders)
    session.add_all(robots)
    session.commit()


# -----------------------------
# Lifecycle
# -----------------------------
#
# @app.on_event("startup")
# async def seed_state() -> None:
#     # Seed only once per process start
#     STATE["orders"] = list(SEED_ORDERS)
#     STATE["robots"] = list(SEED_ROBOTS)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# -----------------------------
# Endpoints (as specified)
# -----------------------------

@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/reset", tags=["simulation"])
async def reset(session: Session = Depends(get_session)):
    seed_data(session=session)
    return {"ok": True}


@app.post("/addOrder", response_model=Order, tags=["orders"])
async def add_order(req: AddOrderRequest,  session: Session = Depends(get_session)) -> Order:
    # Validate nodes exist in graph
    nodes = _graph_nodes_set()
    if req.source not in nodes or req.target not in nodes:
        raise HTTPException(status_code=400, detail="source/target must be valid graph nodes")

    # Enforce unique order name for simplicity
    # todo enfore rule in db
    db_order = Order(name=req.name, source=req.source, target=req.target, status=OrderStatus.NEW)

    session.add(db_order)
    try:
        session.commit()
        session.refresh(db_order)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Order with this name already exists")

    return db_order

@app.get("/getOrders", response_model=List[RetrieveOrderRequest], tags=["orders"])
async def get_orders(session: Session = Depends(get_session)):
    return  session.exec(select(Order)).all()


@app.get("/getRobots", response_model=List[RetrieveRobotRequest], tags=["robots"])
async def get_robots(session: Session = Depends(get_session)):
    return session.exec(select(Robot)).all()

@app.get("/getGraph", response_model=Graph, tags=["graph"])
async def get_graph() -> Graph:
    return GRAPH

# -----------------------------
# Optional: additional stubs to support simulation (Frontend can ignore)
# -----------------------------

class Route(BaseModel):
    robot: str
    path: List[str]  # sequence of node ids

class RoutesResponse(BaseModel):
    routes: List[Route]

# NOTE: These are *stubs* for stretch goals; they currently return empty data.
@app.get("/routes", response_model=RoutesResponse, tags=["simulation"])
async def get_routes() -> RoutesResponse:
    # TODO: Fill with planned paths once a scheduler is implemented server-side
    return RoutesResponse(routes=[])

@app.post("/tick", tags=["simulation"])
async def tick() -> Dict[str, str]:
    # TODO: Advance in-memory simulation: move robots along paths, update order/robot status
    return {"status": "ok", "note": "tick advanced (no-op stub)"}

# -----------------------------
# Run (if executed directly)
# -----------------------------

# Use: uvicorn main:app --reload // or python -m uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
