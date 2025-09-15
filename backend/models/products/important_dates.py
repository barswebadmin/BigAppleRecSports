"""
Important Dates model for product creation
"""

from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime


class ImportantDates(BaseModel):
    """Important dates for league scheduling and registration"""

    seasonStartDate: Union[str, datetime]
    seasonEndDate: Union[str, datetime]
    vetRegistrationStartDateTime: Union[str, datetime]
    earlyRegistrationStartDateTime: Union[str, datetime]
    openRegistrationStartDateTime: Union[str, datetime]
    offDates: Optional[List[Union[str, datetime]]] = None
    newPlayerOrientationDateTime: Optional[Union[str, datetime]] = None
    scoutNightDateTime: Optional[Union[str, datetime]] = None
    openingPartyDate: Optional[Union[str, datetime]] = None
    rainDate: Optional[Union[str, datetime]] = None
    closingPartyDate: Optional[Union[str, datetime]] = None
