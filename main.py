""" Main file for the project """

from fastapi import FastAPI

from src.configs.environment import get_environment_settings
from src.configs.logging import get_logger, setup_default_logging
from src.routers.v1.kandinsky_generator import KandinskyGeneratorRouter
from src.routers.v1.model3d_generator import Model3DGeneratorRouter
from src.routers.v1.simple_generator import SimpleGeneratorRouter

# Setup logging
setup_default_logging()
logger = get_logger(__name__)

# Get environment settings
env = get_environment_settings()
logger.info("Environment settings loaded successfully")

# Initialize FastAPI app
app = FastAPI(
    title="Giga Gen Project",
    description="API for generating images and 3D models using AI",
    version="0.1.0"
)
logger.info("FastAPI application initialized")

# Add routers
app.include_router(SimpleGeneratorRouter)
app.include_router(KandinskyGeneratorRouter)
app.include_router(Model3DGeneratorRouter)
logger.info("All routers registered successfully")


@app.on_event("startup")
async def startup_event() -> None:
    """Startup event handler."""
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Shutdown event handler."""
    logger.info("Application shutdown initiated")
