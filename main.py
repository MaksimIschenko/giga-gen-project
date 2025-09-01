from src.configs.Environment import get_environment_settings
from src.routers.v1.SimpleGeneratorRouter import SimpleGeneratorRouter
from fastapi import FastAPI

env = get_environment_settings()

# Initialize FastAPI app
app = FastAPI()

# Add routers
app.include_router(SimpleGeneratorRouter)

