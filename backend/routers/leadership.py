from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from models.requests import ProcessLeadershipCSVRequest
from services.leadership_service import LeadershipService

router = APIRouter(prefix="/leadership", tags=["leadership"])

@router.post("/addTags")
async def add_leadership_tags(request: ProcessLeadershipCSVRequest) -> Dict[str, Any]:
    """
    Add leadership tags by processing CSV data - extracts emails and handles everything
    This endpoint converts CSV data to objects and extracts emails for processing
    """
    try:
        leadership_service = LeadershipService()
        result = leadership_service.process_leadership_csv(
            csv_data=request.csv_data,
            spreadsheet_title=request.spreadsheet_title,
            year=request.year
        )
        return result
    except Exception as e:
        print(f"❌ Error processing CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for the leadership service"""
    return {"status": "healthy", "service": "leadership"} 