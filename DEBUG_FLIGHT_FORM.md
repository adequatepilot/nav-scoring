# Flight Form Submission Debug Guide

## Issue
Users report persistent "invalid justification 1 select a submission" error when submitting the post-flight form, even with all required fields filled.

## Root Cause Analysis

### Possible Issues

1. **HTML5 Form Validation** (Most Likely)
   - The `<select id="start_gate_id" name="start_gate_id" required>` has an empty option `<option value=""></option>` as the first/default option
   - If user tries to submit without explicitly selecting a gate, the browser shows: "Please select an item in the list"
   - This is browser-native validation, NOT from our code

2. **Form Field Mismatch**
   - Server expects `actual_fuel` as a float
   - Client is sending `actual_fuel_gallons` and `actual_fuel_tenths` as separate fields
   - OR the hidden `actual_fuel` field isn't being populated properly

3. **GPX File Not Being Sent**
   - The form has `enctype="multipart/form-data"` which is correct
   - But the GPX file input might not have a file selected
   - Server validates and returns error, template tries to redisplay but something breaks

4. **JavaScript Preventing Submission**
   - The form's submit handler has validation logic
   - If the logic is preventing submission, the form never reaches the server
   - Console would show the validation error messages

## Debug Steps

### Step 1: Check Browser Console
Open DevTools (F12) and look for these messages:
```
[FLIGHT FORM] Page loaded
[FLIGHT FORM] Form element: (should show form element, not null)
[FLIGHT FORM] Fuel inputs found: true true
[FLIGHT FORM] Start gate select: (should show select element)
[FLIGHT FORM] GPX file input: (should show input element)
```

### Step 2: Check Form Submission
When you click "Submit & Score Flight":
```
[FORM SUBMIT] Form submission started
[FORM SUBMIT] === FORM FIELDS ===
[FORM SUBMIT]   prenav_id: (should be a number)
[FORM SUBMIT]   start_gate_id: (should be a number, NOT empty)
[FORM SUBMIT]   gpx_file: File(filename.gpx, XXXX bytes)
[FORM SUBMIT]   actual_fuel_gallons: (number)
[FORM SUBMIT]   actual_fuel_tenths: (number)
[FORM SUBMIT]   secrets_checkpoint: (number)
[FORM SUBMIT]   secrets_enroute: (number)
[FORM SUBMIT]   actual_fuel: (should be combined, e.g. "8.5")
[FORM SUBMIT] === END FORM FIELDS ===
[FORM SUBMIT] All validations passed, submitting form
```

### Step 3: Check Server Logs
Look for these log lines:
```
POST /flight FORM DEBUG:
  prenav_id=123 (type: int)
  actual_fuel=None (type: None)
  actual_fuel_gallons='8' (type: str)
  actual_fuel_tenths='5' (type: str)
  secrets_checkpoint=0 (type: int)
  secrets_enroute=0 (type: int)
  start_gate_id=456 (type: int)
  gpx_file=UploadFile(...) (type: UploadFile)
POST /flight: User 123 (John Doe) submitting prenav_id=123. is_coach=False, is_admin=False
```

## Expected Behavior

### Scenario 1: Successful Submission
1. User fills form with all valid data
2. Browser console shows: `[FORM SUBMIT] All validations passed, submitting form`
3. Server receives POST with all fields populated
4. Server logs successful processing
5. Redirect to `/results/{result_id}` page

### Scenario 2: Missing Start Gate
1. User skips selecting start gate
2. Browser shows validation error: "Please select an item in the list" (native HTML5 message)
3. Form does NOT submit to server
4. Console shows: `[FORM SUBMIT] ERROR: Start gate not selected!`

### Scenario 3: Missing GPX File
1. User skips selecting GPX file
2. Browser shows validation error: "This field is required" (native HTML5 message)
3. Form does NOT submit to server
4. Console shows: `[FORM SUBMIT] ERROR: GPX file not selected!`

### Scenario 4: Invalid Fuel Values
1. User enters fuel outside valid range
2. JavaScript validation catches it
3. Browser shows alert: "Please enter valid fuel amounts"
4. Form does NOT submit to server
5. Console shows: `[FORM SUBMIT] ERROR: Fuel validation failed`

### Scenario 5: Server-Side Error (e.g., Bad GPX)
1. All client-side validations pass
2. Form submits to server
3. Server detects error (e.g., "GPX file is empty")
4. Server returns form with error message
5. Form is redisplayed with error visible at top
6. User can correct and resubmit

## Testing Checklist

- [ ] Check browser console shows all `[FLIGHT FORM]` and `[FORM SUBMIT]` messages
- [ ] Verify `start_gate_id` is NOT empty in form fields
- [ ] Verify `gpx_file` shows a filename in form fields
- [ ] Check that `actual_fuel` is populated with combined value (e.g., "8.5")
- [ ] Verify server logs show all form parameters received
- [ ] Check for any JavaScript errors in console (red messages)
- [ ] If error occurs, verify form is redisplayed with error message at top
- [ ] If form doesn't submit, check which validation is failing (alert messages)

## Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Start gate not selected | HTML5 validation error "Please select an item" | Select a start gate from dropdown |
| GPX file not selected | HTML5 validation error "This field is required" | Select a GPX file |
| Invalid fuel value | JavaScript alert "Please enter valid fuel amounts" | Enter fuel 0-99 gallons, 0-9 tenths |
| Form seems frozen | No console messages, form unresponsive | Check browser console for JS errors, reload page |
| Error shows "no submission selected" | Form not redisplayed with error | This should be fixed, check server logs |
| Confusing error message | Text like "invalid justification 1 select" | Check console carefully, might be multiple errors concatenated |

## How to Reproduce the Error

### Steps:
1. Go to `/flight/select` page
2. Select a pre-flight submission
3. On the form:
   - Select a start gate ✓
   - Upload a GPX file ✓
   - Enter fuel values ✓
   - Leave secrets at 0 ✓
4. Click "Submit & Score Flight"
5. Open DevTools (F12) and check Console tab
6. Look for the logged form data

### If Submission Fails:
- If no server log appears, it's a client-side issue (check console)
- If server logs appear, it's a server-side error (check error message)
- If "no submission selected" appears, the form redisplay is broken (check selected_prenav)

## Advanced Debugging

### Enable Detailed Logging
The form already includes console.log statements. Look for:
- `[FLIGHT FORM]` - Page load diagnostics
- `[FUEL VALIDATION]` - Fuel input validation
- `[FORM SUBMIT]` - Form submission details

### Server-Side Investigation
Check app logs for:
```
logger.info(f"POST /flight FORM DEBUG:")
logger.info(f"Combined fuel from separate inputs: ...")
logger.warning(f"POST /flight: Error processing prenav_id=...")
logger.info(f"POST /flight: Successfully scored prenav_id=...")
```

### Network Inspection
In DevTools Network tab:
1. Submit form
2. Find the POST request to `/flight`
3. Check "Request Headers" for form data
4. Check "Response" for status code and error message
5. If status is not 303 (redirect), check for error message in HTML response
