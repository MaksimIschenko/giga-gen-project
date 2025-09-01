""" Main file for the project """

from fastapi import FastAPI

from src.configs.environment import get_environment_settings
from src.routers.v1.kandinskyGeneratorRouter import KandinskyGeneratorRouter
from src.routers.v1.simpleGeneratorRouter import SimpleGeneratorRouter

# Get environment settings
env = get_environment_settings()

# Initialize FastAPI app
app = FastAPI()

# Add routers
app.include_router(SimpleGeneratorRouter)
app.include_router(KandinskyGeneratorRouter)

