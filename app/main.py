from fastapi import FastAPI
from dotenv import load_dotenv

from app.core.config import ENV_FILE_PATH
from app.api.project_routes import router as project_router


app = FastAPI(
    title="AutoDocX API",
    description="Automatically scan, understand, and document software projects.",
    version="0.1.0",
)

app.include_router(project_router)


@app.get(
    "/",
    tags=["Health"],
)
def root() -> dict[str, str]:
    return {
        "message": "AutoDocX API is running"
    }


@app.get(
    "/health",
    tags=["Health"],
)
def health_check() -> dict[str, str]:
    return {
        "status": "healthy"
    }


@app.post(
    "/api/config/reload",
    tags=["Config"],
)
def reload_config() -> dict[str, str]:
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
    return {"status": "reloaded"}