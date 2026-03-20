from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import auth, projects, bills, scenarios

# Create all tables on startup (use Alembic for migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Energy Advisor API",
    description="Early-stage energy decision support for buildings",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(bills.router)
app.include_router(scenarios.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
