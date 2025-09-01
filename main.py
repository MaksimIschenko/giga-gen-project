""" Main file for the project """

from fastapi import FastAPI

from src.configs.environment import get_environment_settings
from src.routers.v1.kandinsky_generator import KandinskyGeneratorRouter
from src.routers.v1.model3d_generator import Model3DGeneratorRouter
from src.routers.v1.simple_generator import SimpleGeneratorRouter

# Get environment settings
env = get_environment_settings()

# Initialize FastAPI app
app = FastAPI()

# Add routers
app.include_router(SimpleGeneratorRouter)
app.include_router(KandinskyGeneratorRouter)
app.include_router(Model3DGeneratorRouter)
