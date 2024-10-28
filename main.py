from fastapi import FastAPI
from routes_1 import router
from routes.transactions import transaction_router

app = FastAPI(swagger_ui_parameters={"tryItOutEnabled": True})

app.include_router(router)

app.include_router(transaction_router, prefix="/transactions", tags=["transactions"])