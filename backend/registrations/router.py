from fastapi import APIRouter

router = APIRouter(prefix="/registrations")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
