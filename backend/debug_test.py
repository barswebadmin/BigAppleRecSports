from models.products.product_creation_request import ProductCreationRequest
from models.products.product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)

data_missing_required = {
    "sportName": "Dodgeball",
    "regularSeasonBasicDetails": {
        "year": "2025",
        "season": "Fall",
        "dayOfPlay": "Tuesday",
        "division": "Open",
        "location": "Elliott Center (26th St & 9th Ave)",
        "leagueStartTime": "8:00 PM",
        "leagueEndTime": "11:00 PM",
        "socialOrAdvanced": "Social",
        # Missing sportSubCategory
    },
    "optionalLeagueInfo": {
        # Also missing from here
    },
    "importantDates": {
        "seasonStartDate": "2025-10-15T04:00:00.000Z",
        "seasonEndDate": "2025-12-10T04:00:00.000Z",
        "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
        "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
        "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
    },
    "inventoryInfo": {"price": 150, "totalInventory": 64},
}

try:
    ProductCreationRequest.validate_request_data(data_missing_required)
except ProductCreationRequestValidationError as e:
    errors = e.get_errors()
    for error in errors:
        print(f"Error: {error}")
