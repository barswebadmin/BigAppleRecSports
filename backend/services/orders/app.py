from fastapi import FastAPI

from services.orders.routes import router
from shared.exceptions import install

app = FastAPI(title="orders")
install(app)
app.include_router(router)
