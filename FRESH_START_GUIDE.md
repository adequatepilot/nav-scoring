# Fresh Start Setup Guide for NAV Scoring

Complete step-by-step walkthrough to get from zero to ready-for-competition.

---

## PART 1: DEPLOYMENT (30 minutes)

### Step 1: Clone Repository on New VM

```bash
cd /home/your-user
git clone https://github.com/adequatepilot/nav-scoring.git
cd nav-scoring
```

### Step 2: Run Deployment Script

```bash
bash DEPLOY.sh
```

Follow the prompts:
- It will check for Docker (install if needed)
- You'll be asked for **Zoho SMTP email** and **password**
  - Leave blank for now if you don't have it (can add later)
- Script builds image and starts container

### Step 3: Verify It's Running

```bash
docker-compose logs -f nav-scoring
# Should see: "Uvicorn running on http://0.0.0.0:8000"
# Ctrl+C to exit logs
```

### Step 4: Access the App

Open browser:
```
http://localhost:8000
```

Login with:
- **Email:** admin@siu.edu
- **Password:** admin123

You should see a blank dashboard with no data.

### Step 5: CHANGE THE ADMIN PASSWORD IMMEDIATELY

1. Click **Profile** (top right)
2. Click **Change Password**
3. Enter new secure password
4. Click **Save**

---

## PART 2: CREATE AIRPORTS (10 minutes)

Airports are the starting points for NAV routes.

### Step 6: Go to Airports

1. Click **Admin Functions** → **NAVs**
2. Click **Manage Airports**

### Step 7: Add First Airport

Click **+ Create Airport** button

Fill in:
- **Airport Code:** MDH (or your primary airport)
- **Airport Name:** Madison-Dane County Regional Airport
- **Latitude:** 43.1399
- **Longitude:** -89.3374
- **Elevation (ft):** 887

Click **Create Airport**

### Step 8: Add More Airports (Optional)

Repeat Step 7 for each airport you use. Examples:
- OSH (Oshkosh Wittman) — 43.9854, -88.5563
- JVL (Janesville) — 42.6277, -89.0819
- ORE (Oregon) — 42.6614, -89.3428

**You now have airports in the system.**

---

## PART 3: CREATE NAV ROUTES (30 minutes)

NAV routes are the competition courses. Each route has checkpoints.

### Step 9: Create First NAV Route

1. Go back to **NAVs** → **Manage NAVs**
2. Click **+ Create NAV Route**

Fill in:
- **Airport:** Select "Madison-Dane County Regional Airport"
- **Route Name:** MDH 1 (or "Madison Route 1")
- **Description:** (optional) First competition route

Click **Create Route**

### Step 10: Add Checkpoints to NAV

You should be taken to the route detail page. If not:
1. Click **Manage NAVs**
2. Click the route you just created

Now you'll see **Checkpoints** section with "+ Create Checkpoint" button.

Click **+ Create Checkpoint** to add first checkpoint.

**Example Checkpoint 1:**
- **Name:** Checkpoint 1
- **Latitude:** 43.2100
- **Longitude:** -89.3000
- **Radius:** 0.25 (NM)
- **Sequence:** 1

Click **Create Checkpoint**

### Step 11: Add 4-5 More Checkpoints

For each checkpoint, click **+ Create Checkpoint** and add:

**Example Checkpoint 2:**
- Name: Checkpoint 2
- Latitude: 43.1500
- Longitude: -89.2000
- Radius: 0.25
- Sequence: 2

**Example Checkpoint 3:**
- Name: Checkpoint 3
- Latitude: 43.0800
- Longitude: -89.1500
- Radius: 0.25
- Sequence: 3

**Example Checkpoint 4:**
- Name: Checkpoint 4
- Latitude: 43.1200
- Longitude: -89.0800
- Radius: 0.25
- Sequence: 4

**Example Checkpoint 5 (Return to Start):**
- Name: Return to Start
- Latitude: 43.1399 (same as airport)
- Longitude: -89.3374
- Radius: 0.25
- Sequence: 5

### Step 12: Verify Route is Complete

You should see all 5 checkpoints listed in order. Click **View Route Detail** to see the route on a map.

**You now have a NAV route with checkpoints.**

---

## PART 4: ADD SECRETS (15 minutes)

Secrets are bonus points in the competition. Optional but recommended.

### Step 13: Add Enroute Secret

Go back to your NAV route. Click **Manage Secrets** section.

Click **+ Add Secret**

Fill in:
- **Type:** Enroute (worth 10 points if missed)
- **Latitude:** 43.1650
- **Longitude:** -89.2500
- **Description:** "Red barn on western ridge"

Click **Create Secret**

### Step 14: Add Checkpoint Secrets

For each checkpoint (optional), click **+ Add Secret** for that checkpoint.

**Example Checkpoint 1 Secret:**
- **Type:** Checkpoint
- **Description:** "Three silos"
- Latitude/Longitude: (near checkpoint 1)

Add 1-2 secrets per checkpoint if you want. These are worth 20 points if missed.

**You now have secrets configured.**

---

## PART 5: CREATE USER ACCOUNTS (15 minutes)

Users are your competitors, coaches, and admins.

### Step 15: Go to User Management

1. Click **Admin Functions** → **Manage Users**

### Step 16: Add First Competitor

Click **+ Create User**

Fill in:
- **Name:** John Smith
- **Email:** john.smith@siu.edu
- **Role:** Competitor (or Coach for instructors)
- **Force Password Reset:** Check this box
- Click **Create**

System sends them a confirmation email. They'll set their own password on first login.

### Step 17: Add More Users

Repeat Step 16 for each person:
- At least 2 pilots (competitors)
- At least 2 observers
- Optionally: coaches (for read-only dashboard access)

**Example users to add:**
- Pilot 1: alice.johnson@siu.edu
- Pilot 2: bob.wilson@siu.edu
- Observer 1: carol.davis@siu.edu
- Observer 2: david.brown@siu.edu
- Coach 1: instructor@siu.edu (set Role to Coach)

### Step 18: Approve Pending Users (if they signed up)

If users signed up themselves via `/signup`:
1. Go to **Manage Users**
2. Check **Approved** checkbox for each pending user
3. Click **Save**

**You now have user accounts in the system.**

---

## PART 6: CREATE PAIRINGS (10 minutes)

Pairings pair a pilot with an observer for the competition.

### Step 19: Go to Pairings

1. Click **Admin Functions** → **Manage Pairings**

### Step 20: Create First Pairing

Click **+ Create Pairing**

Fill in:
- **Pilot:** Select "John Smith"
- **Safety Observer:** Select "Carol Davis"
- Click **Create Pairing**

### Step 21: Create More Pairings

Repeat Step 20 for each pilot/observer pair:

**Example:**
- Pilot: Bob Wilson
- Observer: David Brown

**You now have teams (pairings) ready to fly.**

---

## PART 7: ASSIGN NAVs TO TEAMS (10 minutes)

This tells each pairing which NAV route they'll fly.

### Step 22: Go to Assignments

1. Click **Admin Functions** → **Manage Assignments**

### Step 23: Assign NAV to First Pairing

Click **+ Assign NAV**

Fill in:
- **Pairing:** Select "John Smith / Carol Davis"
- **NAV Route:** Select "MDH 1"
- Click **Create Assignment**

System sends them an email: "You've been assigned NAV route MDH 1. You have 48 hours to submit your pre-flight plan."

### Step 24: Assign NAV to Second Pairing

Repeat Step 23:
- Pairing: "Bob Wilson / David Brown"
- NAV: "MDH 1"

**You now have NAVs assigned. Pilots can now submit pre-flight plans!**

---

## PART 8: TEST THE SYSTEM (30 minutes)

### Step 25: Submit a Pre-Flight Plan (as a pilot)

1. Click **Logout** (top right)
2. Login as a competitor: `john.smith@siu.edu` / (their password)
3. You should see **Quick Actions** with big buttons
4. Click **Submit Pre-Flight Plan**

Fill in:
- **Select NAV:** MDH 1
- **Leg 1 Time (MM:SS):** 10:00 (estimate leg 1 will take 10 minutes)
- **Leg 2 Time:** 09:30
- **Leg 3 Time:** 10:15
- **Leg 4 Time:** 09:45
- **Leg 5 Time:** 09:30
- **Total ETE:** 49:00 (sum of legs)
- **Fuel Estimate:** 10.0 gallons
- Click **Submit Pre-Flight Plan**

System generates a **48-hour token**. You'll see it on screen.

### Step 26: Simulate Flight & Submit Post-Flight

Simulate flying the route:
1. Click **Submit Post-Flight Plan**
2. Enter the **token** from step 25
3. Upload a GPX file (or create a dummy one)
4. Enter **Actual Fuel Used:** 9.8 gallons
5. Select **Secrets Found:** (checkboxes for secrets they found)
6. Click **Submit**

System instantly scores the flight:
- Timing penalties (per NIFA Red Book)
- Off-course penalties
- Fuel penalties
- Secret penalties
- **Generates PDF report**

### Step 27: Check Results

1. Click **View Results**
2. You should see the scored flight
3. Click **View PDF** to see the detailed report

---

## PART 9: SYSTEM CONFIGURATION (Optional but Recommended)

### Step 28: Configure Scoring Rules (Admin)

1. Login as admin
2. Click **Admin Functions** → **System Config**
3. Review scoring parameters:
   - Checkpoint radius (default 0.25 NM)
   - Max off-course distance (default 5.0 NM)
   - Fuel error thresholds

Leave defaults unless NIFA rules change.

### Step 29: Test Email Notifications (Admin)

If you added Zoho SMTP credentials:
1. Go to **System Config**
2. Scroll to email settings
3. Click **Test Email** button

Should receive a test email at your Zoho email address.

---

## PART 10: BACKUP STRATEGY

### Step 30: Create First Backup

```bash
bash BACKUP.sh
```

This creates a timestamped backup in `./backups/`

### Step 31: Set Up Daily Backups (Optional)

```bash
crontab -e
```

Add this line:
```
0 2 * * * cd /path/to/nav-scoring && bash BACKUP.sh
```

This runs backup daily at 2 AM.

---

## READY FOR COMPETITION! 🎯

You now have:
✅ Deployment running  
✅ Airports configured  
✅ NAV routes with checkpoints  
✅ Secrets added  
✅ User accounts created  
✅ Pairings set up  
✅ NAVs assigned  
✅ System tested end-to-end  
✅ Backups automated  

---

## QUICK REFERENCE: COMMON TASKS

**Add another NAV route:**
→ NAVs → Create NAV Route → Add checkpoints

**Add more teams:**
→ Users → Create User → Pairings → Create Pairing → Assignments → Assign NAV

**Check flight results:**
→ View Results (or Coach → Results)

**Change scoring parameters:**
→ System Config (admin only)

**Stop/restart the app:**
```bash
docker-compose down
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f nav-scoring
```

**Backup data:**
```bash
bash BACKUP.sh
```

---

**You're all set! Happy flying! ✈️**
