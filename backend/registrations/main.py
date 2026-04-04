from fastapi import FastAPI

from router import router

app = FastAPI(title="BARS Registrations API")
app.include_router(router)
