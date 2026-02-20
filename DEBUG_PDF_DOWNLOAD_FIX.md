# NAV PDF Download Endpoint - Debug Report

## Issue Summary
When Mike clicked "Download PDF" in the NAV packet box on the `/team/assigned-navs` page, the browser opened a new tab showing:
```
detail: not found
```
This is a 404 error indicating the endpoint doesn't exist.

## Root Causes Found

### 1. Missing Database Migration Application
**Location**: Database schema migration file `012_nav_pdf_path.sql`
**Problem**: The migration file existed but had never been applied to the database. The `navs` table was missing the `pdf_path` column that should store the path to uploaded NAV packet PDFs.
**Evidence**:
```sql
-- Before fix:
PRAGMA table_info(navs);
-- Output: id, name, airport_id, created_at (NO pdf_path column)

-- After fix:
PRAGMA table_info(navs);
-- Output: id, name, airport_id, created_at, pdf_path
```

### 2. Missing Backend API Endpoint
**Location**: `/app/app.py`
**Problem**: The frontend template was calling `/coach/navs/{nav_id}/pdf` but this endpoint didn't exist in the FastAPI application. Only `/results/{result_id}/pdf` existed (for flight result PDFs, not NAV packets).
**Evidence**:
- Template code: `<a href="/coach/navs/{{ assignment.nav_id }}/pdf" class="button">`
- Backend search: `grep "@app.get.*pdf"` only found `/results/{result_id}/pdf`

### 3. Missing Database Record Association
**Problem**: Although NAV packet PDFs existed in the file system at `/data/nav_packets/nav_6_1771539824.pdf`, the database record for NAV ID 6 didn't have the `pdf_path` column populated.
**Evidence**:
```sql
-- Before fix:
SELECT id, name, pdf_path FROM navs WHERE id = 6;
-- Error: no such column: pdf_path

-- After fix (with pdf_path populated):
SELECT id, name, pdf_path FROM navs WHERE id = 6;
6|MDH 20|nav_packets/nav_6_1771539824.pdf
```

## Fixes Applied

### Fix 1: Applied Missing Database Migration
**File**: Database
**Change**: Manually applied migration 012_nav_pdf_path.sql
```sql
ALTER TABLE navs ADD COLUMN pdf_path TEXT DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_navs_airport ON navs(airport_id);
```

### Fix 2: Populated Database Record
**File**: Database
**Change**: Set pdf_path for NAV 6 to reference the existing PDF file
```sql
UPDATE navs SET pdf_path = 'nav_packets/nav_6_1771539824.pdf' WHERE id = 6;
```

### Fix 3: Created Missing Backend Endpoint
**File**: `app/app.py`
**Change**: Added new route handler at line 1917
```python
@app.get("/coach/navs/{nav_id}/pdf")
async def download_nav_pdf(nav_id: int, user: dict = Depends(require_login)):
    """Download NAV packet PDF. Available to all authenticated users."""
    # - Retrieves NAV by ID
    # - Verifies pdf_path is set
    # - Resolves file path (handles multiple possible locations)
    # - Verifies file exists on disk
    # - Returns PDF with proper headers and filename
    # - Comprehensive error handling with appropriate HTTP status codes
```

**Key Features**:
- Requires user authentication (all logged-in users can download)
- Robust path resolution (tries multiple possible file locations)
- Handles both absolute and relative paths
- Proper error reporting (distinguishes between NAV not found, PDF not available, file not on disk)
- Returns PDF with user-friendly filename (`{nav_name}_NAV_Packet.pdf`)

### Fix 4: Updated Default Configuration
**File**: `app/app.py` (config defaults)
**Change**: Added `nav_packets` to the default storage paths
```python
"storage": {
    "gpx_uploads": "data/gpx_uploads",
    "pdf_reports": "data/pdf_reports",
    "nav_packets": "data/nav_packets"  # NEW
}
```

### Fix 5: Updated Startup Initialization
**File**: `app/app.py` (startup event handler)
**Change**: Ensured nav_packets directory is created on app initialization
```python
Path(config["storage"]["nav_packets"]).mkdir(parents=True, exist_ok=True)
```

## Verification

### Database State (After Fixes)
```sql
sqlite3 data/navs.db "SELECT id, name, pdf_path FROM navs;"
6|MDH 20|nav_packets/nav_6_1771539824.pdf
7|test|
```

### File System State
```bash
ls -lh /home/michael/clawd/work/nav_scoring/data/nav_packets/
-rw-rw-rw- 1 michael root 6.3M nav_6_1771539824.pdf
file nav_6_1771539824.pdf
# Output: PDF document, version 1.7, 9 page(s)
```

### Code Quality
- Python syntax check: ✓ PASSED (`python3 -m py_compile app/app.py`)

## Expected Behavior After Fixes

When Mike clicks "Download PDF" on the NAV packet box:
1. Browser sends GET request to `/coach/navs/6/pdf`
2. Endpoint retrieves NAV 6 from database
3. Endpoint finds pdf_path value: `nav_packets/nav_6_1771539824.pdf`
4. Endpoint resolves file path to: `/home/michael/clawd/work/nav_scoring/data/nav_packets/nav_6_1771539824.pdf`
5. Endpoint verifies file exists
6. Endpoint returns PDF file with HTTP 200 OK
7. Browser saves/opens the file as `MDH 20_NAV_Packet.pdf`

## Error Cases Handled

| Error Case | HTTP Status | Error Message |
|-----------|-----------|---------------|
| NAV doesn't exist | 404 | "NAV not found" |
| pdf_path not set | 404 | "NAV packet PDF not available" |
| PDF file not on disk | 404 | "PDF file not found on disk" |
| User not authenticated | 401 | (handled by require_login dependency) |
| Internal server error | 500 | "Error downloading PDF: {details}" |

## Files Modified
1. `/home/michael/clawd/work/nav_scoring/app/app.py` - Added endpoint + config updates
2. `/home/michael/clawd/work/nav_scoring/data/navs.db` - Applied migration + populated pdf_path

## Testing Recommendations
1. Verify NAV 6 PDF downloads correctly
2. Test with NAV 7 (no PDF) - should show "NAV packet PDF not available"
3. Test with non-existent NAV ID - should show "NAV not found"
4. Verify downloaded filename is user-friendly
5. Test with logged-out user - should redirect to login
