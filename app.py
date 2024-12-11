from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from routes.transactions import transaction_router
from routes.auth import auth_router
from routes.transaction import t_router
from config.settings import settings

app = FastAPI(swagger_ui_parameters={"tryItOutEnabled": True})

allowed_origins = settings.ALLOWED_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth_router, prefix="/api/v1")

app.include_router(t_router, prefix="/api/v1")

# import uvicorn

# if __name__ == "__main__":
#  uvicorn.run("app:app", host="0.0.0.0", port=8000)