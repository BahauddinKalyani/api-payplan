from fastapi import FastAPI
from routes import router

app = FastAPI(swagger_ui_parameters={"tryItOutEnabled": True})

app.include_router(router)