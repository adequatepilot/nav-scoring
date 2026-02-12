"""
NAV Scoring FastAPI Application
Complete implementation with GPX processing and PDF generation.
"""

import logging
import json
import yaml
import gpxpy
import csv
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import inch
import uvicorn

from app.database import Database
from app.auth import Auth
from app.scoring_engine import NavScoringEngine
from app.email import EmailService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ===== CONFIG LOADING =====

def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load config from YAML file."""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}, using defaults")
        # Return default config
        # Return default config
        return {
            "database": {"path": "data/navs.db"},
            "app": {"title": "NAV Scoring", "version": "1.0.0", "debug": False},
            "session": {
                "cookie_name": "nav_scoring_session",
                "timeout_hours": 24,
                "cookie_secure": False,
                "cookie_httponly": True
            },
            "prenav": {"token_expiry_hours": 48},
            "storage": {
                "gpx_uploads": "data/gpx_uploads",
                "pdf_reports": "data/pdf_reports"
            },
            "scoring": {
                "timing_penalty_per_second": 1.0,
                "off_course": {
                    "max_no_penalty_nm": 0.25,
                    "max_penalty_distance_nm": 5.0,
                    "max_penalty_points": 500
                },
                "fuel_burn": {
                    "over_estimate_multiplier": 500,
                    "under_estimate_threshold": 0.1,
                    "under_estimate_multiplier": 250
                },
                "secrets": {
                    "checkpoint_penalty": 20,
                    "enroute_penalty": 10,
                    "max_distance_miles": 1.0
                }
            },
            "email": {
                "smtp_host": "smtp.zoho.com",
                "smtp_port": 587,
                "sender_email": "nav@example.com",
                "sender_name": "NAV Scoring",
                "sender_password": "",
                "recipients_coach": "coach@example.com"
            }
        }

# ===== APP INITIALIZATION =====

config = load_config()
db = Database(config["database"]["path"])
auth = Auth(db)
scoring_engine = NavScoringEngine(config)
email_service = EmailService(config["email"])

app = FastAPI(
    title=config["app"]["title"],
    version=config["app"]["version"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key-change-this-in-production",
    session_cookie=config["session"]["cookie_name"],
    max_age=config["session"]["timeout_hours"] * 3600,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_path = Path("static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Cleanup on startup
@app.on_event("startup")
async def startup_event():
    """Run cleanup tasks on app startup."""
    logger.info("Running startup tasks...")
    # Cleanup expired verification tokens
    try:
        db.cleanup_expired_verification_pending()
    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}")

# ===== DEPENDENCIES =====

def get_session_user(request: Request) -> Optional[dict]:
    """Get current user from session."""
    return request.session.get("user")

def require_login(request: Request) -> dict:
    """Require any logged-in user."""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_member(request: Request) -> dict:
    """Require competitor (team member, non-coach)."""
    user = require_login(request)
    # Competitors are users with is_coach=0 (but can be is_admin)
    if user.get("is_coach"):
        raise HTTPException(status_code=403, detail="This page is for competitors only")
    return user

def require_competitor(request: Request) -> dict:
    """Alias for require_member."""
    return require_member(request)

def require_coach(request: Request) -> dict:
    """Require coach access (coach or admin)."""
    user = require_login(request)
    if not user.get("is_coach") and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Coach access required")
    return user

def require_admin(request: Request) -> dict:
    """Require admin access."""
    user = require_login(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ===== UTILITY FUNCTIONS =====

def is_smtp_configured() -> bool:
    """Check if SMTP is configured in config.yaml."""
    email_config = config.get("email", {})
    smtp_host = email_config.get("smtp_host", "").strip()
    smtp_password = email_config.get("sender_password", "").strip()
    return bool(smtp_host and smtp_password)

def parse_mmss(time_str: str) -> float:
    """Parse MM:SS or M:SS format to seconds."""
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str}")
    minutes = int(parts[0])
    seconds = int(parts[1])
    return minutes * 60 + seconds

def format_seconds_mmss(seconds: float) -> str:
    """Format seconds as MM:SS."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def parse_gpx(gpx_content: bytes) -> List[Dict]:
    """Parse GPX file and extract track points."""
    try:
        gpx = gpxpy.parse(gpx_content.decode('utf-8'))
        track_points = []
        
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    track_points.append({
                        "lat": point.latitude,
                        "lon": point.longitude,
                        "time": point.time,
                        "speed": point.speed or 0.0,
                        "elevation": point.elevation or 0.0
                    })
        
        logger.info(f"Parsed GPX: {len(track_points)} track points")
        return track_points
    except Exception as e:
        logger.error(f"GPX parsing error: {e}")
        raise ValueError(f"Failed to parse GPX file: {e}")

def generate_track_plot(track_points: List[Dict], checkpoints: List[Dict], output_path: Path):
    """Generate track plot with checkpoints."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot track
    lats = [p["lat"] for p in track_points]
    lons = [p["lon"] for p in track_points]
    ax.plot(lons, lats, 'b-', linewidth=2, label='Flight Track')
    
    # Plot checkpoints
    cp_lats = [cp["lat"] for cp in checkpoints]
    cp_lons = [cp["lon"] for cp in checkpoints]
    ax.scatter(cp_lons, cp_lats, c='red', s=100, marker='o', label='Checkpoints', zorder=5)
    
    # Labels
    for i, cp in enumerate(checkpoints):
        ax.text(cp["lon"], cp["lat"], f"  {cp['name']}", fontsize=9, ha='left')
    
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Flight Track')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Track plot saved: {output_path}")

def generate_pdf_report(
    result_data: Dict,
    nav_data: Dict,
    pairing_data: Dict,
    plot_path: Path,
    output_path: Path
):
    """Generate PDF report with results."""
    c = pdf_canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1*inch, height - 1*inch, "NAV Scoring - Flight Results")
    
    # Flight info
    c.setFont("Helvetica", 12)
    y = height - 1.5*inch
    c.drawString(1*inch, y, f"NAV: {nav_data['name']}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Pilot: {pairing_data['pilot_name']}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Observer: {pairing_data['observer_name']}")
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Date: {result_data['scored_at'][:10]}")
    
    # Overall score
    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, y, f"Overall Score: {result_data['overall_score']:.0f} points")
    c.setFont("Helvetica", 10)
    y -= 0.2*inch
    c.drawString(1*inch, y, "(Lower is better)")
    
    # Summary metrics
    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "Summary")
    c.setFont("Helvetica", 11)
    
    y -= 0.3*inch
    c.drawString(1*inch, y, f"Total Time Score: {result_data['total_time_score']:.0f} pts")
    y -= 0.25*inch
    c.drawString(1*inch, y, f"Fuel Penalty: {result_data['fuel_penalty']:.0f} pts")
    y -= 0.25*inch
    secrets_penalty = result_data['checkpoint_secrets_penalty'] + result_data['enroute_secrets_penalty']
    c.drawString(1*inch, y, f"Secrets Penalty: {secrets_penalty:.0f} pts")
    
    # Add track plot
    y -= 0.5*inch
    if plot_path.exists():
        try:
            c.drawImage(str(plot_path), 1*inch, y - 4*inch, width=5*inch, height=4*inch)
            y -= 4.5*inch
        except Exception as e:
            logger.error(f"Failed to add plot to PDF: {e}")
    
    # Checkpoint details (new page if needed)
    if y < 2*inch:
        c.showPage()
        y = height - 1*inch
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "Checkpoint Details")
    y -= 0.3*inch
    
    c.setFont("Helvetica", 9)
    for cp in result_data['checkpoint_results']:
        if y < 1*inch:
            c.showPage()
            y = height - 1*inch
        
        c.drawString(1*inch, y, f"{cp['name']}: {cp['method']} - {cp['distance_nm']:.3f} NM - Score: {cp['leg_score']:.0f} pts")
        y -= 0.2*inch
    
    c.save()
    logger.info(f"PDF report saved: {output_path}")

# ===== PUBLIC ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to appropriate page based on auth status and role."""
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Route based on role
    if user.get("is_coach"):
        return RedirectResponse(url="/coach", status_code=303)
    else:
        return RedirectResponse(url="/team", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login form."""
    user = get_session_user(request)
    if user:
        if user.get("is_coach"):
            return RedirectResponse(url="/coach", status_code=303)
        else:
            return RedirectResponse(url="/team", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Display signup form."""
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    
    # Check if SMTP is configured
    smtp_configured = is_smtp_configured()
    
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "smtp_configured": smtp_configured,
        "smtp_error": None if smtp_configured else "Self-signup is currently disabled. Please contact an administrator."
    })

@app.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...)
):
    """Handle self-signup with email verification."""
    # Check if SMTP is configured
    if not is_smtp_configured():
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Self-signup is currently disabled. Please contact an administrator.",
            "smtp_configured": False
        })
    
    # Validate password confirmation
    if password != password_confirm:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match",
            "smtp_configured": True
        })

    # Validate password strength
    if len(password) < 6:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Password must be at least 6 characters",
            "smtp_configured": True
        })

    # Attempt signup (stores in verification_pending)
    result = auth.signup(email, name, password)
    if not result["success"]:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": result["message"],
            "smtp_configured": True
        })

    # Send verification email
    verification_token = result.get("verification_token")
    if verification_token:
        try:
            # Build verification link with request host
            host = request.headers.get("host", "localhost:8000")
            scheme = request.url.scheme
            verification_link = f"{scheme}://{host}/verify?token={verification_token}"
            await email_service.send_verification_email(
                email=email,
                name=name,
                verification_link=verification_link
            )
            logger.info(f"Verification email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            # Even if email fails, show the message to user
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "error": "Verification email could not be sent. Please contact support.",
                "smtp_configured": True
            })

    # Signup successful - show confirmation message
    return templates.TemplateResponse("signup_confirmation.html", {
        "request": request,
        "email": email
    })

@app.get("/verify")
async def verify_email(request: Request, token: str):
    """Verify email and create user account."""
    result = auth.verify_email(token)
    
    if not result["success"]:
        return templates.TemplateResponse("verify_email.html", {
            "request": request,
            "success": False,
            "message": result["message"]
        })
    
    # Email verified and user created, redirect to login
    return templates.TemplateResponse("verify_email.html", {
        "request": request,
        "success": True,
        "message": "Email verified! Your account has been created and is awaiting admin approval. You will be able to log in once approved."
    })

@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle unified login for all users (email-based)."""
    result = auth.login(email, password)
    
    if not result["success"]:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": result["message"]
        })
    
    # Store in session
    user_data = result["user"]
    request.session["user"] = {
        "user_id": user_data["id"],
        "email": user_data["email"],
        "name": user_data["name"],
        "is_coach": user_data["is_coach"],
        "is_admin": user_data["is_admin"]
    }
    
    # Redirect based on role
    if user_data["is_coach"]:
        return RedirectResponse(url="/coach", status_code=303)
    else:
        return RedirectResponse(url="/team", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    """Logout user."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/team", response_class=HTMLResponse)
async def team_dashboard(request: Request, user: dict = Depends(require_competitor)):
    """Team member main dashboard."""
    # Get pairing info
    pairing = db.get_active_pairing_for_member(user["user_id"])
    pairing_data = None
    
    if pairing:
        pilot = db.get_member_by_id(pairing["pilot_id"])
        observer = db.get_member_by_id(pairing["safety_observer_id"])
        pairing_data = {
            "id": pairing["id"],
            "pilot_name": pilot["name"] if pilot else "Unknown",
            "observer_name": observer["name"] if observer else "Unknown"
        }
    
    # Get recent results for this user's pairings
    pairings = db.list_pairings_for_member(user["user_id"], active_only=False)
    pairing_ids = [p["id"] for p in pairings]
    
    recent_results = []
    for pairing_id in pairing_ids:
        pairing_results = db.list_flight_results(pairing_id=pairing_id)
        recent_results.extend(pairing_results)
    
    # Sort by date descending and take top 5
    recent_results.sort(key=lambda r: r["scored_at"], reverse=True)
    recent_results = recent_results[:5]
    
    # Enhance with NAV names
    for result in recent_results:
        nav = db.get_nav(result["nav_id"])
        result["nav_name"] = nav["name"] if nav else "Unknown"
    
    return templates.TemplateResponse("team/dashboard.html", {
        "request": request,
        "pairing_info": pairing_data,
        "recent_results": recent_results,
        "member_name": user["name"]
    })

# ===== MEMBER ROUTES =====

@app.get("/prenav", response_class=HTMLResponse)
async def prenav_form(request: Request, user: dict = Depends(require_member)):
    """Display pre-flight form."""
    navs = db.list_navs()
    
    # Get pairing info
    pairing = db.get_active_pairing_for_member(user["user_id"])
    pairing_data = None
    
    if pairing:
        pilot = db.get_member_by_id(pairing["pilot_id"])
        observer = db.get_member_by_id(pairing["safety_observer_id"])
        pairing_data = {
            "id": pairing["id"],
            "pilot_name": pilot["name"] if pilot else "Unknown",
            "observer_name": observer["name"] if observer else "Unknown"
        }
    
    # Add checkpoint counts to navs
    for nav in navs:
        checkpoints = db.get_checkpoints(nav["id"])
        nav["checkpoints"] = checkpoints
    
    return templates.TemplateResponse("team/prenav.html", {
        "request": request,
        "navs": navs,
        "pairing": pairing_data,
        "member_name": user["name"]
    })

@app.post("/prenav")
async def submit_prenav(
    request: Request,
    user: dict = Depends(require_member),
    nav_id: int = Form(...),
    leg_times_str: str = Form(...),
    total_time_str: str = Form(...),
    fuel_estimate: float = Form(...)
):
    """Submit pre-flight plan."""
    try:
        logger.info(f"Prenav submission from user {user['user_id']}: nav_id={nav_id}, fuel_estimate={fuel_estimate}")
        
        # Get pairing
        pairing = db.get_active_pairing_for_member(user["user_id"])
        if not pairing:
            logger.error(f"No active pairing found for user {user['user_id']}")
            raise HTTPException(status_code=400, detail="No active pairing found")
        
        # Verify user is pilot
        if pairing["pilot_id"] != user["user_id"]:
            logger.error(f"User {user['user_id']} is not the pilot (pilot_id={pairing['pilot_id']})")
            raise HTTPException(status_code=403, detail="Only pilot can submit pre-flight plan")
        
        # Parse times
        try:
            leg_times_list = json.loads(leg_times_str)
            leg_times = [parse_mmss(t) for t in leg_times_list]
            total_time = parse_mmss(total_time_str)
            logger.info(f"Parsed times: {leg_times} (total={total_time}s)")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing times: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")
        
        # Generate token
        token = Auth.generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=config["prenav"]["token_expiry_hours"])
        
        prenav_id = db.create_prenav(
            pairing_id=pairing["id"],
            pilot_id=user["user_id"],
            nav_id=nav_id,
            leg_times=leg_times,
            total_time=total_time,
            fuel_estimate=fuel_estimate,
            token=token,
            expires_at=expires_at
        )
        
        logger.info(f"Created prenav: ID={prenav_id}, token={token}")
        
        # Get NAV name
        nav = db.get_nav(nav_id)
        
        # Get observer email
        observer = db.get_member_by_id(pairing["safety_observer_id"])
        
        # Send emails to both pilot and observer
        pilot_email = user["email"]
        observer_email = observer["email"] if observer else ""
        
        try:
            await email_service.send_prenav_confirmation(
                team_email=pilot_email,
                team_name=user["name"],
                nav_name=nav["name"],
                token=token
            )
            
            if observer_email:
                await email_service.send_prenav_confirmation(
                    team_email=observer_email,
                    team_name=observer["name"],
                    nav_name=nav["name"],
                    token=token
                )
        except Exception as email_err:
            logger.warning(f"Email send failed (non-critical): {email_err}")
        
        logger.info(f"Prenav submitted successfully, redirecting to confirmation")
        # Redirect to confirmation page instead of returning template
        return RedirectResponse(url=f"/prenav_confirmation?token={token}", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting prenav: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/prenav_confirmation", response_class=HTMLResponse)
async def prenav_confirmation(request: Request, user: dict = Depends(require_member), token: str = None):
    """Display pre-flight confirmation page."""
    prenav = db.get_prenav_by_token(token) if token else None
    if not prenav:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    expires_at = datetime.fromisoformat(prenav["expires_at"])
    
    return templates.TemplateResponse("team/prenav_confirmation.html", {
        "request": request,
        "token": token,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M UTC"),
        "member_name": user["name"]
    })

@app.get("/flight", response_class=HTMLResponse)
async def flight_form(request: Request, user: dict = Depends(require_member)):
    """Display post-flight form."""
    # Get all start gates (we'll filter by airport later if needed)
    # For now, get all gates
    gates = []
    navs = db.list_navs()
    for nav in navs:
        nav_gates = db.get_start_gates(nav["airport_id"])
        for gate in nav_gates:
            if gate not in gates:
                gates.append(gate)
    
    return templates.TemplateResponse("team/flight.html", {
        "request": request,
        "start_gates": gates,
        "member_name": user["name"]
    })

@app.post("/flight")
async def submit_flight(
    request: Request,
    user: dict = Depends(require_member),
    prenav_token: str = Form(...),
    actual_fuel: float = Form(...),
    secrets_checkpoint: int = Form(...),
    secrets_enroute: int = Form(...),
    start_gate_id: int = Form(...),
    gpx_file: UploadFile = File(...)
):
    """Submit post-flight GPX and process scoring."""
    try:
        # Validate prenav token
        prenav = db.get_prenav_by_token(prenav_token)
        if not prenav:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        # Get pairing
        pairing = db.get_pairing(prenav["pairing_id"])
        if not pairing:
            raise HTTPException(status_code=400, detail="Pairing not found")
        
        # Verify user is part of pairing
        if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
            raise HTTPException(status_code=403, detail="Token does not belong to this team")
        
        # Check expiry
        expires_at = datetime.fromisoformat(prenav["expires_at"])
        if expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token has expired")
        
        # Save GPX file
        gpx_storage = Path(config["storage"]["gpx_uploads"])
        gpx_storage.mkdir(parents=True, exist_ok=True)
        
        gpx_filename = f"gpx_{pairing['id']}_{prenav['nav_id']}_{int(datetime.utcnow().timestamp())}.gpx"
        gpx_path = gpx_storage / gpx_filename
        
        gpx_content = await gpx_file.read()
        gpx_path.write_bytes(gpx_content)
        
        # Parse GPX
        track_points = parse_gpx(gpx_content)
        if not track_points:
            raise HTTPException(status_code=400, detail="No track points found in GPX file")
        
        # Get NAV and checkpoints
        nav = db.get_nav(prenav["nav_id"])
        checkpoints = nav["checkpoints"]
        
        # Get start gate
        start_gate = db.get_start_gate(start_gate_id)
        if not start_gate:
            raise HTTPException(status_code=400, detail="Invalid start gate")
        
        # Detect start gate crossing
        start_crossing, start_distance = scoring_engine.detect_start_gate_crossing(
            track_points, start_gate
        )
        
        if not start_crossing:
            raise HTTPException(status_code=400, detail="Could not detect start gate crossing")
        
        # Score checkpoints
        checkpoint_results = []
        previous_point = start_crossing
        previous_time = start_crossing["time"].timestamp()
        
        for i, checkpoint in enumerate(checkpoints):
            timing_point, distance_nm, method, within_025 = scoring_engine.find_checkpoint_crossing(
                track_points, checkpoint, previous_point, previous_time
            )
            
            if not timing_point:
                logger.error(f"Could not find crossing for checkpoint {checkpoint['name']}")
                continue
            
            # Calculate leg score
            estimated_time = prenav["leg_times"][i]
            actual_time = timing_point["time"].timestamp() - previous_time
            
            leg_score, off_course_penalty = scoring_engine.calculate_leg_score(
                actual_time, estimated_time, distance_nm, within_025
            )
            
            checkpoint_results.append({
                "name": checkpoint["name"],
                "distance_nm": distance_nm,
                "within_0_25_nm": within_025,
                "method": method,
                "estimated_time": estimated_time,
                "actual_time": actual_time,
                "deviation": actual_time - estimated_time,
                "leg_score": leg_score,
                "off_course_penalty": off_course_penalty
            })
            
            previous_point = timing_point
            previous_time = timing_point["time"].timestamp()
        
        # Calculate total scores
        total_time_deviation = sum(abs(cp["deviation"]) for cp in checkpoint_results)
        total_time_score = sum(cp["leg_score"] for cp in checkpoint_results)
        
        fuel_penalty = scoring_engine.calculate_fuel_penalty(
            prenav["fuel_estimate"], actual_fuel
        )
        
        checkpoint_secrets_penalty, enroute_secrets_penalty = scoring_engine.calculate_secrets_penalty(
            secrets_checkpoint, secrets_enroute
        )
        
        checkpoint_scores = [(cp["leg_score"], cp["off_course_penalty"]) for cp in checkpoint_results]
        
        overall_score = scoring_engine.calculate_overall_score(
            checkpoint_scores,
            total_time_score,
            fuel_penalty,
            checkpoint_secrets_penalty,
            enroute_secrets_penalty
        )
        
        # Generate track plot
        pdf_storage = Path(config["storage"]["pdf_reports"])
        pdf_storage.mkdir(parents=True, exist_ok=True)
        
        plot_filename = f"plot_{pairing['id']}_{prenav['nav_id']}_{int(datetime.utcnow().timestamp())}.png"
        plot_path = pdf_storage / plot_filename
        
        generate_track_plot(track_points, checkpoints, plot_path)
        
        # Generate PDF
        pdf_filename = f"result_{pairing['id']}_{prenav['nav_id']}_{int(datetime.utcnow().timestamp())}.pdf"
        pdf_path = pdf_storage / pdf_filename
        
        # Get pairing member names
        pilot = db.get_member_by_id(pairing["pilot_id"])
        observer = db.get_member_by_id(pairing["safety_observer_id"])
        
        pairing_display = {
            "pilot_name": pilot["name"] if pilot else "Unknown",
            "observer_name": observer["name"] if observer else "Unknown"
        }
        
        result_data_for_pdf = {
            "overall_score": overall_score,
            "total_time_score": total_time_score,
            "fuel_penalty": fuel_penalty,
            "checkpoint_secrets_penalty": checkpoint_secrets_penalty,
            "enroute_secrets_penalty": enroute_secrets_penalty,
            "checkpoint_results": checkpoint_results,
            "scored_at": datetime.utcnow().isoformat()
        }
        
        generate_pdf_report(result_data_for_pdf, nav, pairing_display, plot_path, pdf_path)
        
        # Save result to database
        result_id = db.create_flight_result(
            prenav_id=prenav["id"],
            pairing_id=pairing["id"],
            nav_id=prenav["nav_id"],
            gpx_filename=gpx_filename,
            actual_fuel=actual_fuel,
            secrets_checkpoint=secrets_checkpoint,
            secrets_enroute=secrets_enroute,
            start_gate_id=start_gate_id,
            overall_score=overall_score,
            checkpoint_results=checkpoint_results
        )
        
        # Update with PDF filename
        from app.database import Database as DB
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE flight_results SET pdf_filename = ? WHERE id = ?",
                (pdf_filename, result_id)
            )
        
        # Send emails
        pilot_email = pilot["email"] if pilot else ""
        observer_email = observer["email"] if observer else ""
        
        team_name = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Team"
        
        if pilot_email:
            await email_service.send_results_notification(
                team_email=pilot_email,
                team_name=pilot["name"],
                nav_name=nav["name"],
                overall_score=overall_score,
                pdf_filename=pdf_filename
            )
        
        if observer_email:
            await email_service.send_results_notification(
                team_email=observer_email,
                team_name=observer["name"],
                nav_name=nav["name"],
                overall_score=overall_score,
                pdf_filename=pdf_filename
            )
        
        # Redirect to results page
        return RedirectResponse(url=f"/results/{result_id}", status_code=303)
    
    except Exception as e:
        logger.error(f"Error processing flight: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/results/{result_id}", response_class=HTMLResponse)
async def view_result(request: Request, result_id: int, user: dict = Depends(require_member)):
    """View specific result."""
    result = db.get_flight_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Verify user is part of pairing
    pairing = db.get_pairing(result["pairing_id"])
    if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
        raise HTTPException(status_code=403, detail="Not authorized to view this result")
    
    # Get NAV
    nav = db.get_nav(result["nav_id"])
    
    # Get prenav
    prenav = db.get_prenav(result["prenav_id"])
    
    # Build result display
    result_display = {
        "id": result["id"],
        "overall_score": result["overall_score"],
        "checkpoint_results": result["checkpoint_results"],
        "total_time_score": sum(cp["leg_score"] for cp in result["checkpoint_results"]),
        "total_deviation": sum(abs(cp["deviation"]) for cp in result["checkpoint_results"]),
        "fuel_penalty": 0,  # Calculate from prenav and actual
        "checkpoint_secrets_penalty": result["secrets_missed_checkpoint"] * config["scoring"]["secrets"]["checkpoint_penalty"],
        "enroute_secrets_penalty": result["secrets_missed_enroute"] * config["scoring"]["secrets"]["enroute_penalty"],
        "estimated_fuel_burn": prenav["fuel_estimate"],
        "actual_fuel_burn": result["actual_fuel"],
        "pdf_filename": result.get("pdf_filename"),
        "scored_at": result["scored_at"]
    }
    
    # Recalculate fuel penalty
    fuel_penalty = scoring_engine.calculate_fuel_penalty(
        prenav["fuel_estimate"], result["actual_fuel"]
    )
    result_display["fuel_penalty"] = fuel_penalty
    
    return templates.TemplateResponse("team/results.html", {
        "request": request,
        "result": result_display,
        "nav": nav,
        "member_name": user["name"]
    })

@app.get("/results/{result_id}/pdf")
async def download_pdf(result_id: int, user: dict = Depends(require_member)):
    """Download PDF report."""
    result = db.get_flight_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Verify authorization
    pairing = db.get_pairing(result["pairing_id"])
    if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if not result.get("pdf_filename"):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_path = Path(config["storage"]["pdf_reports"]) / result["pdf_filename"]
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=result["pdf_filename"])

@app.get("/results", response_class=HTMLResponse)
async def list_results(request: Request, user: dict = Depends(require_member)):
    """List all results for user's pairings."""
    pairings = db.list_pairings_for_member(user["user_id"], active_only=False)
    pairing_ids = [p["id"] for p in pairings]
    
    results = []
    for pairing_id in pairing_ids:
        pairing_results = db.list_flight_results(pairing_id=pairing_id)
        results.extend(pairing_results)
    
    # Sort by date descending
    results.sort(key=lambda r: r["scored_at"], reverse=True)
    
    # Enhance with NAV and pairing names
    for result in results:
        nav = db.get_nav(result["nav_id"])
        result["nav_name"] = nav["name"] if nav else "Unknown"
        
        pairing = db.get_pairing(result["pairing_id"])
        if pairing:
            pilot = db.get_member_by_id(pairing["pilot_id"])
            observer = db.get_member_by_id(pairing["safety_observer_id"])
            result["team_name"] = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Unknown"
    
    return templates.TemplateResponse("team/results.html", {
        "request": request,
        "results": results,
        "member_name": user["name"]
    })

# ===== COACH ROUTES =====

@app.get("/coach", response_class=HTMLResponse)
async def coach_dashboard(request: Request, user: dict = Depends(require_coach)):
    """Coach main dashboard."""
    members = db.list_members()
    pairings = db.list_pairings(active_only=True)
    results = db.list_flight_results()
    
    # Get pending approvals count (for admins)
    pending_users = db.list_users(filter_type="pending")
    pending_count = len(pending_users)
    
    # Recent results (last 5)
    recent = results[:5] if results else []
    
    # Enhance recent results
    for result in recent:
        nav = db.get_nav(result["nav_id"])
        result["nav_name"] = nav["name"] if nav else "Unknown"
        
        pairing = db.get_pairing(result["pairing_id"])
        if pairing:
            pilot = db.get_member_by_id(pairing["pilot_id"])
            observer = db.get_member_by_id(pairing["safety_observer_id"])
            result["team_name"] = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Unknown"
    
    return templates.TemplateResponse("coach/dashboard.html", {
        "request": request,
        "is_admin": user.get("is_admin", False),
        "pending_count": pending_count,
        "stats": {
            "total_members": len(members),
            "active_pairings": len(pairings),
            "recent_results": len(results)
        },
        "recent_results": recent
    })

@app.get("/coach/results", response_class=HTMLResponse)
async def coach_results(
    request: Request,
    user: dict = Depends(require_coach),
    pairing_id: Optional[int] = None,
    nav_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Coach view results."""
    # Apply filters
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date + "T23:59:59") if end_date else None
    
    results = db.list_flight_results(
        pairing_id=pairing_id,
        nav_id=nav_id,
        start_date=start_dt,
        end_date=end_dt
    )
    
    # Enhance results
    for result in results:
        nav = db.get_nav(result["nav_id"])
        result["nav_name"] = nav["name"] if nav else "Unknown"
        
        pairing = db.get_pairing(result["pairing_id"])
        if pairing:
            pilot = db.get_member_by_id(pairing["pilot_id"])
            observer = db.get_member_by_id(pairing["safety_observer_id"])
            result["pilot_name"] = pilot["name"] if pilot else "Unknown"
            result["observer_name"] = observer["name"] if observer else "Unknown"
        
        # Calculate component scores
        prenav = db.get_prenav(result["prenav_id"])
        if prenav:
            fuel_penalty = scoring_engine.calculate_fuel_penalty(
                prenav["fuel_estimate"], result["actual_fuel"]
            )
            result["fuel_penalty"] = fuel_penalty
            result["total_time_score"] = sum(cp["leg_score"] for cp in result["checkpoint_results"])
    
    # Get all pairings and NAVs for filter dropdowns
    pairings = db.list_pairings(active_only=False)
    for pairing in pairings:
        pilot = db.get_member_by_id(pairing["pilot_id"])
        observer = db.get_member_by_id(pairing["safety_observer_id"])
        pairing["pilot_name"] = pilot["name"] if pilot else "Unknown"
        pairing["observer_name"] = observer["name"] if observer else "Unknown"
    
    navs = db.list_navs()
    
    return templates.TemplateResponse("coach/results.html", {
        "request": request,
        "results": results,
        "pairings": pairings,
        "navs": navs,
        "selected_pairing": pairing_id,
        "selected_nav": nav_id,
        "start_date": start_date or "",
        "end_date": end_date or ""
    })

@app.get("/coach/results/{result_id}", response_class=HTMLResponse)
async def coach_view_result(request: Request, result_id: int, user: dict = Depends(require_coach)):
    """Coach view specific result (reuse member view)."""
    result = db.get_flight_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    nav = db.get_nav(result["nav_id"])
    prenav = db.get_prenav(result["prenav_id"])
    
    result_display = {
        "id": result["id"],
        "overall_score": result["overall_score"],
        "checkpoint_results": result["checkpoint_results"],
        "total_time_score": sum(cp["leg_score"] for cp in result["checkpoint_results"]),
        "total_deviation": sum(abs(cp["deviation"]) for cp in result["checkpoint_results"]),
        "fuel_penalty": scoring_engine.calculate_fuel_penalty(prenav["fuel_estimate"], result["actual_fuel"]),
        "checkpoint_secrets_penalty": result["secrets_missed_checkpoint"] * config["scoring"]["secrets"]["checkpoint_penalty"],
        "enroute_secrets_penalty": result["secrets_missed_enroute"] * config["scoring"]["secrets"]["enroute_penalty"],
        "estimated_fuel_burn": prenav["fuel_estimate"],
        "actual_fuel_burn": result["actual_fuel"],
        "pdf_filename": result.get("pdf_filename"),
        "scored_at": result["scored_at"]
    }
    
    return templates.TemplateResponse("team/results.html", {
        "request": request,
        "result": result_display,
        "nav": nav,
        "member_name": "Coach"
    })

@app.get("/coach/results/{result_id}/delete")
async def coach_delete_result(result_id: int, user: dict = Depends(require_coach)):
    """Delete a result."""
    result = db.get_flight_result(result_id)
    if result:
        # Delete files
        if result.get("gpx_filename"):
            gpx_path = Path(config["storage"]["gpx_uploads"]) / result["gpx_filename"]
            if gpx_path.exists():
                gpx_path.unlink()
        
        if result.get("pdf_filename"):
            pdf_path = Path(config["storage"]["pdf_reports"]) / result["pdf_filename"]
            if pdf_path.exists():
                pdf_path.unlink()
        
        # Delete from DB
        db.delete_flight_result(result_id)
    
    return RedirectResponse(url="/coach/results", status_code=303)

@app.get("/coach/members", response_class=HTMLResponse)
async def coach_members(request: Request, user: dict = Depends(require_coach), filter_type: str = "all"):
    """Member management - now using unified users table."""
    members = db.list_users(filter_type=filter_type)
    return templates.TemplateResponse("coach/members.html", {
        "request": request,
        "members": members,
        "current_filter": filter_type
    })

@app.post("/coach/members/update")
async def update_user_role(
    request: Request,
    user: dict = Depends(require_admin)
):
    """Update user role (is_approved, is_coach, is_admin). Admin only."""
    try:
        body = await request.json()
        user_id = body.get("user_id")
        field = body.get("field")
        value = body.get("value")
        
        if not all([user_id, field, value is not None]):
            return {"success": False, "message": "Missing required fields"}
        
        # Validate field
        if field not in ["is_approved", "is_coach", "is_admin"]:
            return {"success": False, "message": "Invalid field"}
        
        # Update user
        success = db.update_user(user_id, **{field: 1 if value else 0})
        
        if success:
            logger.info(f"User {user_id} updated: {field}={value}")
            return {"success": True, "message": f"User {field} updated"}
        else:
            return {"success": False, "message": "User not found"}
    
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/members/{user_id}/delete")
async def delete_user_route(
    user_id: int,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Delete a user. Admin only."""
    try:
        success = db.delete_user(user_id)
        if success:
            logger.info(f"User {user_id} deleted")
            return RedirectResponse(url="/coach/members?message=User deleted", status_code=303)
        else:
            return RedirectResponse(url="/coach/members?error=User not found", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return RedirectResponse(url=f"/coach/members?error={str(e)}", status_code=303)

@app.post("/coach/members")
async def coach_create_member(
    request: Request,
    user: dict = Depends(require_coach),
    email: str = Form(...),
    name: str = Form(...),
    password: Optional[str] = Form(None)
):
    """Create new user (unified users table). New users are created as pending approval."""
    try:
        # Create user in unified users table with is_approved=False (pending)
        # For coach-created accounts, email is already verified
        password_hash = auth.hash_password(password) if password else ""
        user_id = db.create_user(
            username=email,  # Email is now the login credential
            password_hash=password_hash,
            email=email,
            name=name,
            is_coach=False,
            is_admin=False,
            is_approved=False,  # Pending admin approval
            email_verified=True  # Coach-created accounts have verified email
        )
        logger.info(f"New user created (pending approval): {email} (ID: {user_id})")
        return RedirectResponse(url="/coach/members?message=User created (pending approval)", status_code=303)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return RedirectResponse(url=f"/coach/members?error={str(e)}", status_code=303)

@app.post("/coach/members/bulk")
async def coach_bulk_members(
    request: Request,
    user: dict = Depends(require_coach),
    csv_file: UploadFile = File(...)
):
    """Bulk import members from CSV."""
    try:
        content = await csv_file.read()
        csv_text = content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_text))
        
        count = 0
        for row in reader:
            if len(row) >= 2:
                email = row[0].strip()
                name = row[1].strip()
                
                # Skip if email already exists
                if db.get_user_by_email(email):
                    logger.warning(f"Skipping duplicate email: {email}")
                    continue
                
                # Create user (email is used as username for coach-created accounts)
                try:
                    db.create_user(
                        username=email,
                        password_hash="",  # No password initially
                        email=email,
                        name=name,
                        is_coach=False,
                        is_admin=False,
                        is_approved=False,  # Pending approval
                        email_verified=True  # Coach-imported, so email is verified
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Error creating user {email}: {e}")
        
        return RedirectResponse(url=f"/coach/members?message=Created {count} members", status_code=303)
    except Exception as e:
        logger.error(f"Error bulk creating members: {e}")
        return RedirectResponse(url=f"/coach/members?error={str(e)}", status_code=303)

@app.get("/coach/members/{member_id}/deactivate")
async def coach_deactivate_member(member_id: int, user: dict = Depends(require_coach)):
    """Deactivate member."""
    db.update_member(member_id, is_active=0)
    return RedirectResponse(url="/coach/members", status_code=303)

@app.get("/coach/members/{member_id}/activate")
async def coach_activate_member(member_id: int, user: dict = Depends(require_coach)):
    """Activate member."""
    db.update_member(member_id, is_active=1)
    return RedirectResponse(url="/coach/members", status_code=303)

@app.get("/coach/pairings", response_class=HTMLResponse)
async def coach_pairings(request: Request, user: dict = Depends(require_coach)):
    """Pairing management."""
    members = db.list_active_members()
    active_pairings = db.list_pairings(active_only=True)
    inactive_pairings = [p for p in db.list_pairings(active_only=False) if not p["is_active"]]
    
    # Enhance pairings
    for pairing in active_pairings + inactive_pairings:
        pilot = db.get_member_by_id(pairing["pilot_id"])
        observer = db.get_member_by_id(pairing["safety_observer_id"])
        pairing["pilot_name"] = pilot["name"] if pilot else "Unknown"
        pairing["observer_name"] = observer["name"] if observer else "Unknown"
    
    return templates.TemplateResponse("coach/pairings.html", {
        "request": request,
        "members": members,
        "active_pairings": active_pairings,
        "inactive_pairings": inactive_pairings
    })

@app.post("/coach/pairings")
async def coach_create_pairing(
    request: Request,
    user: dict = Depends(require_coach),
    pilot_id: int = Form(...),
    safety_observer_id: int = Form(...)
):
    """Create pairing."""
    try:
        pairing_id = db.create_pairing(pilot_id, safety_observer_id)
        return RedirectResponse(url="/coach/pairings?message=Pairing created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating pairing: {e}")
        return RedirectResponse(url=f"/coach/pairings?error={str(e)}", status_code=303)

@app.get("/coach/pairings/{pairing_id}/break")
async def coach_break_pairing(pairing_id: int, user: dict = Depends(require_coach)):
    """Break pairing."""
    db.break_pairing(pairing_id)
    return RedirectResponse(url="/coach/pairings", status_code=303)

@app.get("/coach/pairings/{pairing_id}/reactivate")
async def coach_reactivate_pairing(pairing_id: int, user: dict = Depends(require_coach)):
    """Reactivate pairing."""
    db.update_pairing(pairing_id, is_active=1)
    return RedirectResponse(url="/coach/pairings", status_code=303)

@app.get("/coach/pairings/{pairing_id}/delete")
async def coach_delete_pairing(pairing_id: int, user: dict = Depends(require_coach)):
    """Delete pairing."""
    db.delete_pairing(pairing_id)
    return RedirectResponse(url="/coach/pairings", status_code=303)

@app.get("/coach/navs", response_class=HTMLResponse)
async def coach_navs(request: Request, user: dict = Depends(require_coach)):
    """NAV management dashboard."""
    airports = db.list_airports()
    navs = db.list_navs()
    
    # Enhance with counts
    for airport in airports:
        airport["gates_count"] = len(db.get_start_gates(airport["id"]))
        airport["navs_count"] = len(db.list_navs_by_airport(airport["id"]))
    
    return templates.TemplateResponse("coach/navs.html", {
        "request": request,
        "airports": airports,
        "navs": navs
    })

@app.get("/coach/navs/airports", response_class=HTMLResponse)
async def coach_manage_airports(request: Request, user: dict = Depends(require_coach)):
    """Manage airports."""
    airports = db.list_airports()
    return templates.TemplateResponse("coach/navs_airports.html", {
        "request": request,
        "airports": airports
    })

@app.post("/coach/navs/airports")
async def coach_create_airport(
    request: Request,
    user: dict = Depends(require_coach),
    code: str = Form(...)
):
    """Create airport."""
    try:
        code = code.strip().upper()
        if not code:
            raise ValueError("Airport code cannot be empty")
        airport_id = db.create_airport(code)
        return RedirectResponse(url="/coach/navs/airports?message=Airport created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating airport: {e}")
        return RedirectResponse(url=f"/coach/navs/airports?error={str(e)}", status_code=303)

@app.get("/coach/navs/airports/{airport_id}/delete")
async def coach_delete_airport(airport_id: int, user: dict = Depends(require_coach)):
    """Delete airport."""
    try:
        db.delete_airport(airport_id)
        return RedirectResponse(url="/coach/navs/airports?message=Airport deleted", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting airport: {e}")
        return RedirectResponse(url=f"/coach/navs/airports?error={str(e)}", status_code=303)

@app.get("/coach/navs/gates/{airport_id}", response_class=HTMLResponse)
async def coach_manage_gates(request: Request, airport_id: int, user: dict = Depends(require_coach)):
    """Manage start gates for airport."""
    airport = db.get_airport(airport_id)
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    
    gates = db.get_start_gates(airport_id)
    return templates.TemplateResponse("coach/navs_gates.html", {
        "request": request,
        "airport": airport,
        "gates": gates
    })

@app.post("/coach/navs/gates")
async def coach_create_gate(
    request: Request,
    user: dict = Depends(require_coach),
    airport_id: int = Form(...),
    name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...)
):
    """Create start gate."""
    try:
        gate_id = db.create_start_gate(airport_id, name, lat, lon)
        return RedirectResponse(url=f"/coach/navs/gates/{airport_id}?message=Gate created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating gate: {e}")
        return RedirectResponse(url=f"/coach/navs/gates/{airport_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/gates/{gate_id}/delete")
async def coach_delete_gate(gate_id: int, user: dict = Depends(require_coach)):
    """Delete start gate."""
    try:
        gate = db.get_start_gate(gate_id)
        if not gate:
            raise HTTPException(status_code=404, detail="Gate not found")
        airport_id = gate["airport_id"]
        db.delete_start_gate(gate_id)
        return RedirectResponse(url=f"/coach/navs/gates/{airport_id}?message=Gate deleted", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting gate: {e}")
        airport_id = request.query_params.get("airport_id", 1)
        return RedirectResponse(url=f"/coach/navs/gates/{airport_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/routes", response_class=HTMLResponse)
async def coach_manage_routes(request: Request, user: dict = Depends(require_coach)):
    """Manage NAV routes."""
    airports = db.list_airports()
    navs = db.list_navs()
    
    # Enhance navs with airport name and checkpoint count
    for nav in navs:
        airport = db.get_airport(nav["airport_id"])
        nav["airport_code"] = airport["code"] if airport else "Unknown"
        nav["checkpoints_count"] = len(db.get_checkpoints(nav["id"]))
    
    return templates.TemplateResponse("coach/navs_routes.html", {
        "request": request,
        "airports": airports,
        "navs": navs
    })

@app.post("/coach/navs/routes")
async def coach_create_route(
    request: Request,
    user: dict = Depends(require_coach),
    name: str = Form(...),
    airport_id: int = Form(...)
):
    """Create NAV route."""
    try:
        name = name.strip()
        if not name:
            raise ValueError("Route name cannot be empty")
        nav_id = db.create_nav(name, airport_id)
        return RedirectResponse(url="/coach/navs/routes?message=Route created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating route: {e}")
        return RedirectResponse(url=f"/coach/navs/routes?error={str(e)}", status_code=303)

@app.get("/coach/navs/routes/{nav_id}/delete")
async def coach_delete_route(nav_id: int, user: dict = Depends(require_coach)):
    """Delete NAV route."""
    try:
        db.delete_nav(nav_id)
        return RedirectResponse(url="/coach/navs/routes?message=Route deleted", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting route: {e}")
        return RedirectResponse(url=f"/coach/navs/routes?error={str(e)}", status_code=303)

@app.get("/coach/navs/checkpoints/{nav_id}", response_class=HTMLResponse)
async def coach_manage_checkpoints(request: Request, nav_id: int, user: dict = Depends(require_coach)):
    """Manage checkpoints for a NAV."""
    nav = db.get_nav(nav_id)
    if not nav:
        raise HTTPException(status_code=404, detail="NAV not found")
    
    checkpoints = db.get_checkpoints(nav_id)
    return templates.TemplateResponse("coach/navs_checkpoints.html", {
        "request": request,
        "nav": nav,
        "checkpoints": checkpoints
    })

@app.post("/coach/navs/checkpoints")
async def coach_create_checkpoint(
    request: Request,
    user: dict = Depends(require_coach),
    nav_id: int = Form(...),
    name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    sequence: int = Form(...)
):
    """Create checkpoint."""
    try:
        checkpoint_id = db.create_checkpoint(nav_id, sequence, name, lat, lon)
        return RedirectResponse(url=f"/coach/navs/checkpoints/{nav_id}?message=Checkpoint created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating checkpoint: {e}")
        return RedirectResponse(url=f"/coach/navs/checkpoints/{nav_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/checkpoints/{checkpoint_id}/delete")
async def coach_delete_checkpoint(checkpoint_id: int, user: dict = Depends(require_coach)):
    """Delete checkpoint."""
    try:
        checkpoint = db.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        nav_id = checkpoint["nav_id"]
        db.delete_checkpoint(checkpoint_id)
        return RedirectResponse(url=f"/coach/navs/checkpoints/{nav_id}?message=Checkpoint deleted", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting checkpoint: {e}")
        nav_id = request.query_params.get("nav_id", 1)
        return RedirectResponse(url=f"/coach/navs/checkpoints/{nav_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/secrets/{nav_id}", response_class=HTMLResponse)
async def coach_manage_secrets(request: Request, nav_id: int, user: dict = Depends(require_coach)):
    """Manage secrets for a NAV."""
    nav = db.get_nav(nav_id)
    if not nav:
        raise HTTPException(status_code=404, detail="NAV not found")
    
    secrets = db.get_secrets(nav_id)
    return templates.TemplateResponse("coach/navs_secrets.html", {
        "request": request,
        "nav": nav,
        "secrets": secrets
    })

@app.post("/coach/navs/secrets")
async def coach_create_secret(
    request: Request,
    user: dict = Depends(require_coach),
    nav_id: int = Form(...),
    name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    secret_type: str = Form(...)
):
    """Create secret."""
    try:
        if secret_type not in ("checkpoint", "enroute"):
            raise ValueError("Invalid secret type")
        secret_id = db.create_secret(nav_id, name, lat, lon, secret_type)
        return RedirectResponse(url=f"/coach/navs/secrets/{nav_id}?message=Secret created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating secret: {e}")
        return RedirectResponse(url=f"/coach/navs/secrets/{nav_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/secrets/{secret_id}/delete")
async def coach_delete_secret(secret_id: int, user: dict = Depends(require_coach)):
    """Delete secret."""
    try:
        secret = db.get_secret(secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        nav_id = secret["nav_id"]
        db.delete_secret(secret_id)
        return RedirectResponse(url=f"/coach/navs/secrets/{nav_id}?message=Secret deleted", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting secret: {e}")
        nav_id = request.query_params.get("nav_id", 1)
        return RedirectResponse(url=f"/coach/navs/secrets/{nav_id}?error={str(e)}", status_code=303)

@app.get("/coach/config", response_class=HTMLResponse)
async def coach_config(request: Request, user: dict = Depends(require_admin)):
    """View/edit config (admin only)."""
    config_data = config["scoring"]
    email_config = config.get("email", {})
    
    return templates.TemplateResponse("coach/config.html", {
        "request": request,
        "config": config_data,
        "email_config": email_config
    })

@app.post("/coach/config")
async def coach_update_config(
    request: Request,
    user: dict = Depends(require_admin),
    timing_penalty_per_second: float = Form(...),
    off_course_max_no_penalty: float = Form(...),
    off_course_max_penalty_distance: float = Form(...),
    off_course_max_penalty_points: float = Form(...),
    fuel_over_estimate_multiplier: float = Form(...),
    fuel_under_estimate_threshold: float = Form(...),
    fuel_under_estimate_multiplier: float = Form(...),
    secrets_checkpoint_penalty: float = Form(...),
    secrets_enroute_penalty: float = Form(...),
    secrets_max_distance: float = Form(...)
):
    """Update config."""
    try:
        # Update config dict
        config["scoring"]["timing_penalty_per_second"] = timing_penalty_per_second
        config["scoring"]["off_course"]["max_no_penalty_nm"] = off_course_max_no_penalty
        config["scoring"]["off_course"]["max_penalty_distance_nm"] = off_course_max_penalty_distance
        config["scoring"]["off_course"]["max_penalty_points"] = off_course_max_penalty_points
        config["scoring"]["fuel_burn"]["over_estimate_multiplier"] = fuel_over_estimate_multiplier
        config["scoring"]["fuel_burn"]["under_estimate_threshold"] = fuel_under_estimate_threshold
        config["scoring"]["fuel_burn"]["under_estimate_multiplier"] = fuel_under_estimate_multiplier
        config["scoring"]["secrets"]["checkpoint_penalty"] = secrets_checkpoint_penalty
        config["scoring"]["secrets"]["enroute_penalty"] = secrets_enroute_penalty
        config["scoring"]["secrets"]["max_distance_miles"] = secrets_max_distance
        
        # Save to file
        config_path = Path("config/config.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump(config, default_flow_style=False))
        
        # Recreate scoring engine with new config
        global scoring_engine
        scoring_engine = NavScoringEngine(config)
        
        return RedirectResponse(url="/coach/config?message=Config updated successfully", status_code=303)
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return RedirectResponse(url=f"/coach/config?error={str(e)}", status_code=303)

@app.post("/coach/config/email")
async def coach_update_email_config(
    request: Request,
    user: dict = Depends(require_admin),
    smtp_host: str = Form(...),
    smtp_port: int = Form(...),
    from_email: str = Form(...),
    from_name: str = Form(...),
    smtp_username: str = Form(...),
    smtp_password: str = Form(...)
):
    """Update email/SMTP configuration (admin only)."""
    try:
        # Update email config
        config["email"]["smtp_host"] = smtp_host
        config["email"]["smtp_port"] = smtp_port
        config["email"]["sender_email"] = from_email
        config["email"]["sender_name"] = from_name
        config["email"]["smtp_username"] = smtp_username
        
        # Only update password if provided (not empty/placeholder)
        if smtp_password and smtp_password not in ["••••••••", ""]:
            config["email"]["sender_password"] = smtp_password
        
        # Save to file
        config_path = Path("config/config.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump(config, default_flow_style=False))
        
        # Reload email service with new config
        global email_service
        email_service = EmailService(config["email"])
        
        return RedirectResponse(url="/coach/config?message=Email config updated successfully", status_code=303)
    except Exception as e:
        logger.error(f"Error updating email config: {e}")
        return RedirectResponse(url=f"/coach/config?error={str(e)}", status_code=303)

# ===== STARTUP/SHUTDOWN =====

@app.on_event("startup")
async def startup_event():
    """App startup."""
    logger.info("NAV Scoring app starting up")
    deleted = db.delete_expired_prenavs()
    if deleted:
        logger.info(f"Deleted {deleted} expired pre-NAV submissions")
    
    # Ensure storage directories exist
    Path(config["storage"]["gpx_uploads"]).mkdir(parents=True, exist_ok=True)
    Path(config["storage"]["pdf_reports"]).mkdir(parents=True, exist_ok=True)

@app.on_event("shutdown")
async def shutdown_event():
    """App shutdown."""
    logger.info("NAV Scoring app shutting down")

if __name__ == "__main__":
    uvicorn.run(
        "app.app:app",
        host="0.0.0.0",
        port=8000,
        reload=config["app"]["debug"],
    )
