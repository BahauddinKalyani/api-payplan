from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from routes.transactions import transaction_router
from routes.auth import auth_router
from routes.transaction import t_router

app = FastAPI(swagger_ui_parameters={"tryItOutEnabled": True})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth_router, prefix="/api/v1")

# app.include_router(transaction_router, prefix="/transactions", tags=["transactions"])

app.include_router(t_router, prefix="/api/v1")