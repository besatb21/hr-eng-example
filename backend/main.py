import heapq
import json
from enum import Enum
# -----------------------------
# Persistence With SQLite Setup
# -----------------------------
from typing import Annotated
from typing import Dict, List, Tuple, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# models_sqlite.py
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select, Field


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
    status: OrderStatus = OrderStatus.NEW


class RouteOrderLink(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    route_json: str
    order_id: int = Field(default=None, foreign_key="order.id")
    distance: int


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


class AssignOrderRequest(BaseModel):
    name: str
    source: str


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


GRAPH: Graph = Graph(nodes=["A", "B", "C", "D", "E", "F"],
    edges=[Edge(**{"from_": "A", "to": "B", "weight": 1}), Edge(**{"from_": "B", "to": "C", "weight": 2}),
        Edge(**{"from_": "C", "to": "D", "weight": 2}), Edge(**{"from_": "B", "to": "E", "weight": 3}),
        Edge(**{"from_": "E", "to": "F", "weight": 1}), Edge(**{"from_": "D", "to": "F", "weight": 2}),
        # Treat edges as undirected for simplicity; callers may add both directions explicitly if desired
    ], )

SEED_ROBOTS = [Robot(name="R1", status=RobotStatus.IDLE, node="A"),
    Robot(name="R2", status=RobotStatus.EXECUTING, node="C"), Robot(name="R3", status=RobotStatus.IDLE, node="E"), ]

SEED_ORDERS = [Order(name="O-1001", source="B", target="D", status=OrderStatus.NEW), ]

# -----------------------------
# App Setup
# -----------------------------

app = FastAPI(title="AGV Scheduling Exercise API", version="0.1.0",
    description=("Minimal backend stubs for the AGV fleet scheduling exercise.\n\n"
                 "Endpoints provided: /addOrder, /getOrders, /getGraph, /getRobots.\n"
                 "State is in-memory and resets on restart."), )

# CORS for local dev frontends (Vite/Next/CRA)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173",  # Vite default
    "http://localhost:3000",  # CRA/Next.js
    "*",  # loosen for exercise; tighten for prod
], allow_credentials=True, allow_methods=["*"], allow_headers=["*"], )


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


## todo mention the use of ChatGPT in the implementation of Dijkstra's algorithm and the use of copilot in adding this comment
def find_shortest_path(from_: str, to: str, graph: 'Graph') -> Tuple[float, List[str]]:
    # Build adjacency list from edges
    adj: Dict[str, List[Tuple[str, float]]] = {node: [] for node in graph.nodes}
    for edge in graph.edges:
        adj[edge.from_].append((edge.to, edge.weight))
        adj[edge.to].append((edge.from_, edge.weight))  # treat as undirected

    # Dijkstra setup
    distances: Dict[str, float] = {node: float('inf') for node in graph.nodes}
    previous: Dict[str, Optional[str]] = {node: None for node in graph.nodes}
    distances[from_] = 0

    # Min-heap: (distance, node)
    heap = [(0, from_)]

    while heap:
        current_dist, current_node = heapq.heappop(heap)
        if current_node == to:
            break  # early exit

        if current_dist > distances[current_node]:
            continue

        for neighbor, weight in adj[current_node]:
            distance = current_dist + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current_node
                heapq.heappush(heap, (distance, neighbor))

    # Reconstruct shortest path
    path = []
    node = to
    while node is not None:
        path.append(node)
        node = previous[node]
    path.reverse()

    if distances[to] == float('inf'):
        return float('inf'), []  # no path found

    return distances[to], path


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
    SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)
    seed_data(session=session)
    return {"ok": True}


@app.post("/addOrder", response_model=Order, tags=["orders"])
async def add_order(req: AddOrderRequest, session: Session = Depends(get_session)) -> Order:
    # Validate nodes exist in graph
    nodes = _graph_nodes_set()
    if req.source not in nodes or req.target not in nodes:
        raise HTTPException(status_code=400, detail="source/target must be valid graph nodes")

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
    return session.exec(select(Order)).all()


@app.get("/getRobots", response_model=List[RetrieveRobotRequest], tags=["robots"])
async def get_robots(session: Session = Depends(get_session)):
    return session.exec(select(Robot)).all()


@app.get("/getGraph", response_model=Graph, tags=["graph"])
async def get_graph() -> Graph:
    return GRAPH


@app.post("/assignNearestIdleRobot", tags=["scheduling"])
async def assign_nearest_idle_robot(order: AssignOrderRequest, session: Session = Depends(get_session)):
    # todo validate order exists
    assigned_order = session.exec(select(Order).where(Order.name == order.name)).first()
    if not assigned_order:
        raise HTTPException(status_code=404, detail="Order not found")
    robots = list(session.exec(select(Robot)).all())

    path_for_robot = []
    for robot in robots:
        if robot.status == RobotStatus.IDLE:
            distance, path = find_shortest_path(robot.node, order.source, GRAPH)
            path_for_robot.append({"robot": robot, "distance": distance, "path": path})

    if not path_for_robot:
        raise HTTPException(status_code=404, detail="No idle robot available")

    resulting_path = sorted(path_for_robot, key=lambda x: (x["distance"], x["robot"].name))[0]
    chosen_robot, path = resulting_path["robot"], resulting_path["path"]
    assigned_order.status = OrderStatus.IN_PROGRESS
    assigned_robot = session.exec(select(Robot).where(Robot.id == chosen_robot.id)).first()
    assigned_robot.status = RobotStatus.EXECUTING
    order_path = RouteOrderLink(route_json=json.dumps(path), order_id=assigned_order.id, distance=len(path))

    session.add(assigned_order)
    session.add(assigned_robot)
    session.add(order_path)
    session.commit()
    return {"robot_name": chosen_robot.name, "path": path}


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
