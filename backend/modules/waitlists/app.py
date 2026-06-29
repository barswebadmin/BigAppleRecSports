from fastapi import FastAPI

from services.waitlists.routes import router
from shared.exceptions import install

app = FastAPI(title="waitlists")
install(app)
app.include_router(router)
