from fastapi import FastAPI

from services.refunds.routes import router
from shared.exceptions import install

app = FastAPI(title="refunds")
install(app)
app.include_router(router)
