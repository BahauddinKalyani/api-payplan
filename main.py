from fastapi import FastAPI
from routes.transactions import transaction_router
from routes.auth import auth_router

app = FastAPI(swagger_ui_parameters={"tryItOutEnabled": True})

app.include_router(auth_router)

app.include_router(transaction_router, prefix="/transactions", tags=["transactions"])