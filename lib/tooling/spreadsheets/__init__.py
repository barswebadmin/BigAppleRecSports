"""Spreadsheet data transformation and parsing utilities.

Pure functions for working with spreadsheet data (list of rows). No I/O.
For Google Sheets API clients, see backend/modules/integrations/google/.

Public API:
    - get_cell: Safe cell access with strip and default.
    - rows_to_dicts: Convert rows to list of dicts using headers.
    - filter_blank_rows: Remove rows where required columns are blank.
    - parse_tabs_metadata: Parse tab info from Sheets API response.
    - TabInfo: Dataclass for tab metadata.
"""

from lib.tooling.spreadsheets.helpers import (
    TabInfo,
    filter_blank_rows,
    get_cell,
    parse_tabs_metadata,
    rows_to_dicts,
)
