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
import asyncio
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import uvicorn

from app.database import Database
from app.auth import Auth
from app.scoring_engine import NavScoringEngine
from app.email import EmailService
from app.backup_scheduler import BackupScheduler
from app.pdf_generator import (
    generate_full_route_map,
    generate_checkpoint_detail_map,
    generate_enhanced_pdf_report
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ===== CONFIG LOADING =====

def load_config(config_path: str = "data/config.yaml") -> dict:
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
                "pdf_reports": "data/pdf_reports",
                "nav_packets": "data/nav_packets"
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
            },
            "backup": {
                "enabled": True,
                "frequency_hours": 24,
                "retention_days": 7,
                "backup_path": "data/backups",
                "max_backups": 10
            }
        }

# ===== APP INITIALIZATION =====

config = load_config()
db = Database(config["database"]["path"])
auth = Auth(db)
scoring_engine = NavScoringEngine(config)
email_service = EmailService(config["email"])
backup_scheduler = BackupScheduler(
    config.get("backup", {}),
    config["database"]["path"]
)
backup_task = None  # Will be set during startup

app = FastAPI(
    title=config["app"]["title"],
    version=config["app"]["version"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Add Jinja2 filters for penalty breakdown display
def format_time(seconds):
    """Format seconds as MM:SS"""
    if isinstance(seconds, (int, float)):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    return str(seconds)

def format_signed(value):
    """Format number with +/- sign"""
    if isinstance(value, (int, float)):
        if value >= 0:
            return f"+{value:.0f}"
        else:
            return f"{value:.0f}"
    return str(value)

templates.env.filters['format_time'] = format_time
templates.env.filters['format_signed'] = format_signed

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

# Profile pictures (persistent storage in data directory)
profile_pics_path = Path("data/profile_pictures")
profile_pics_path.mkdir(parents=True, exist_ok=True)
app.mount("/profile_pictures", StaticFiles(directory=str(profile_pics_path)), name="profile_pictures")

# Serve NAV packet PDFs
@app.get("/nav-packets/{filename}")
async def download_nav_packet(filename: str):
    """Download NAV packet PDF."""
    pdf_path = Path(config["storage"].get("nav_packets", "data/nav_packets")) / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)

# Cleanup on startup
@app.on_event("startup")
async def startup_event():
    """Run cleanup and initialization tasks on app startup."""
    global backup_task
    logger.info("Running startup tasks...")
    
    # Cleanup expired verification tokens
    try:
        db.cleanup_expired_verification_pending()
    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}")
    
    # Try to cleanup expired prenavs
    try:
        deleted = db.delete_expired_prenavs()
        if deleted:
            logger.info(f"Deleted {deleted} expired pre-NAV submissions")
    except Exception as e:
        logger.warning(f"Could not delete expired prenavs on startup (likely first run): {e}")
    
    # Ensure storage directories exist
    try:
        Path(config["storage"]["gpx_uploads"]).mkdir(parents=True, exist_ok=True)
        Path(config["storage"]["pdf_reports"]).mkdir(parents=True, exist_ok=True)
        Path(config["storage"]["nav_packets"]).mkdir(parents=True, exist_ok=True)
        Path(config.get("backup", {}).get("backup_path", "data/backups")).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating storage directories: {e}")
    
    # Initialize backup scheduler
    try:
        if backup_scheduler.enabled:
            # Start background backup task (first backup will run after frequency_hours)
            backup_task = asyncio.create_task(backup_scheduler.start_background_task())
            logger.info("Backup scheduler started")
    except Exception as e:
        logger.error(f"Error initializing backup scheduler: {e}")

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
        # Can't redirect from dependency function, use error template
        raise HTTPException(
            status_code=403, 
            detail="This page is for competitors only. Please use the Coach Dashboard instead."
        )
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

def get_initials(name: str) -> str:
    """Get initials from name (first letter of first and last words)."""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1:
        return parts[0][0:2].upper()
    else:
        return "?"

def get_avatar_color(name: str) -> str:
    """Get a consistent color class for a name based on hash."""
    colors = ["avatar-color-1", "avatar-color-2", "avatar-color-3", 
              "avatar-color-4", "avatar-color-5", "avatar-color-6"]
    color_index = sum(ord(c) for c in name) % len(colors)
    return colors[color_index]

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
    """Generate PDF report with results including comprehensive penalty breakdown."""
    # Create PDF document
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.black,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph("NAV Scoring - Flight Results", title_style))
    
    # Flight info
    info_style = styles['Normal']
    story.append(Paragraph(f"<b>NAV:</b> {nav_data['name']}", info_style))
    story.append(Paragraph(f"<b>Pilot:</b> {pairing_data['pilot_name']}", info_style))
    story.append(Paragraph(f"<b>Observer:</b> {pairing_data['observer_name']}", info_style))
    story.append(Paragraph(f"<b>Date:</b> {result_data['scored_at'][:10]}", info_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Overall score
    score_style = ParagraphStyle(
        'ScoreStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"Overall Score: {result_data['overall_score']:.0f} points (Lower is better)", score_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Penalty Breakdown Table
    story.append(Paragraph("<b>Penalty Breakdown</b>", styles['Heading3']))
    story.append(Spacer(1, 0.15*inch))
    
    # Build penalty breakdown data
    penalty_data = [
        ['Category', 'Estimate', 'Actual', 'Deviation', 'Points'],
        ['TIMING PENALTIES', '', '', '', ''],
    ]
    
    # Add checkpoint rows
    for i, cp in enumerate(result_data['checkpoint_results']):
        est_time = f"{int(cp['estimated_time']//60):02d}:{int(cp['estimated_time']%60):02d}"
        act_time = f"{int(cp['actual_time']//60):02d}:{int(cp['actual_time']%60):02d}"
        penalty_data.append([
            f"Leg {i+1}: {cp['name']}",
            est_time,
            act_time,
            f"{cp['deviation']:+.0f}s",
            f"{cp['leg_score']:.0f}"
        ])
    
    # Subtotal leg penalties
    penalty_data.append([
        'Subtotal: Leg Penalties',
        '',
        '',
        '',
        f"{result_data['leg_penalties']:.0f}"
    ])
    
    # Total time penalty
    est_total = f"{int(result_data.get('estimated_total_time', 0)//60):02d}:{int(result_data.get('estimated_total_time', 0)%60):02d}"
    act_total = f"{int(result_data.get('actual_total_time', 0)//60):02d}:{int(result_data.get('actual_total_time', 0)%60):02d}"
    penalty_data.append([
        'Total Time',
        est_total,
        act_total,
        f"{result_data.get('total_time_deviation', 0):+.0f}s",
        f"{result_data['total_time_penalty']:.0f}"
    ])
    
    # Timing subtotal
    penalty_data.append([
        'TIMING SUBTOTAL',
        '',
        '',
        '',
        f"{result_data['total_time_score']:.0f}"
    ])
    
    penalty_data.append(['', '', '', '', ''])  # Blank row
    
    # Off-course penalties
    penalty_data.append(['OFF-COURSE PENALTIES', '', '', '', ''])
    for cp in result_data['checkpoint_results']:
        within = '✓ Inside' if cp.get('within_0_25_nm') else f"{max(0, cp['distance_nm'] - 0.25):.3f} NM over"
        penalty_data.append([
            cp['name'],
            'Within 0.25 NM',
            f"{cp['distance_nm']:.3f} NM",
            within,
            f"{cp['off_course_penalty']:.0f}"
        ])
    
    penalty_data.append([
        'Subtotal: Off-Course',
        '',
        '',
        '',
        f"{result_data.get('total_off_course', sum(cp['off_course_penalty'] for cp in result_data['checkpoint_results'])):.0f}"
    ])
    
    penalty_data.append(['', '', '', '', ''])  # Blank row
    
    # Fuel penalty
    penalty_data.append(['FUEL PENALTY', '', '', '', ''])
    fuel_pct = result_data.get('fuel_error_pct', 0)
    fuel_diff = result_data.get('actual_fuel_burn', 0) - result_data.get('estimated_fuel_burn', 0)
    penalty_data.append([
        'Fuel Burn',
        f"{result_data.get('estimated_fuel_burn', 0):.1f} gal",
        f"{result_data.get('actual_fuel_burn', 0):.1f} gal",
        f"{fuel_diff:+.2f} gal ({fuel_pct:+.1f}%)",
        f"{result_data['fuel_penalty']:.0f}"
    ])
    
    penalty_data.append(['', '', '', '', ''])  # Blank row
    
    # Secrets penalties
    penalty_data.append(['SECRETS PENALTIES', '', '', '', ''])
    penalty_data.append([
        'Checkpoint secrets missed',
        '-',
        f"{result_data.get('secrets_missed_checkpoint', 0)}",
        '-',
        f"{result_data['checkpoint_secrets_penalty']:.0f}"
    ])
    penalty_data.append([
        'Enroute secrets missed',
        '-',
        f"{result_data.get('secrets_missed_enroute', 0)}",
        '-',
        f"{result_data['enroute_secrets_penalty']:.0f}"
    ])
    
    penalty_data.append([
        'Subtotal: Secrets',
        '',
        '',
        '',
        f"{result_data['checkpoint_secrets_penalty'] + result_data['enroute_secrets_penalty']:.0f}"
    ])
    
    # Create table
    penalty_table = Table(penalty_data, colWidths=[2.2*inch, 1*inch, 1*inch, 1.2*inch, 0.8*inch])
    penalty_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.white]),
    ]))
    
    story.append(penalty_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Add track plot
    if plot_path.exists():
        try:
            story.append(PageBreak())
            story.append(Paragraph("<b>Flight Track</b>", styles['Heading3']))
            story.append(Spacer(1, 0.15*inch))
            img = Image(str(plot_path), width=6*inch, height=4.5*inch)
            story.append(img)
        except Exception as e:
            logger.error(f"Failed to add plot to PDF: {e}")
    
    # Build PDF
    doc.build(story)
    logger.info(f"PDF report saved: {output_path}")

# ===== PUBLIC ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to appropriate page based on auth status and role."""
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Redirect all users to unified dashboard
    return RedirectResponse(url="/dashboard", status_code=303)

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
    """Handle unified login for all users (email-based). Issue 13: Check for password reset flag."""
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
    
    # Issue 13: Check if user must reset password
    if user_data.get("must_reset_password", 0) == 1:
        request.session["must_reset_password"] = True
        logger.info(f"User {user_data['email']} must reset password on login")
        return RedirectResponse(url="/reset-password", status_code=303)
    
    # Redirect all to unified dashboard
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    """Logout user."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def unified_dashboard(request: Request, user: dict = Depends(require_login)):
    """Unified dashboard for all users - content adapts based on role."""
    is_coach = user.get("is_coach", False)
    is_admin = user.get("is_admin", False)
    
    if is_coach or is_admin:
        # Coach/Admin dashboard
        members = db.list_users(filter_type="approved")
        pairings = db.list_pairings(active_only=True)
        results = db.list_flight_results()
        
        # Recent results (last 5)
        recent = results[:5] if results else []
        
        # Enhance recent results
        for result in recent:
            nav = db.get_nav(result["nav_id"])
            result["nav_name"] = nav["name"] if nav else "Unknown"
            
            pairing = db.get_pairing(result["pairing_id"])
            if pairing:
                pilot = db.get_user_by_id(pairing["pilot_id"])
                observer = db.get_user_by_id(pairing["safety_observer_id"])
                result["team_name"] = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Unknown"
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "member_name": user["name"],
            "is_coach": is_coach,
            "is_admin": is_admin,
            "stats": {
                "total_users": len(members),
                "active_pairings": len(pairings),
                "recent_results": len(results)
            },
            "recent_results": recent,
            "pairing_info": None
        })
    else:
        # Competitor dashboard
        # Get pairing info
        pairing = db.get_active_pairing_for_member(user["user_id"])
        pairing_data = None
        assigned_navs_count = 0
        
        if pairing:
            pilot = db.get_user_by_id(pairing["pilot_id"])
            observer = db.get_user_by_id(pairing["safety_observer_id"])
            
            # Build pilot data with profile picture
            pilot_picture = None
            if pilot and pilot.get("profile_picture_path"):
                # Extract filename from "profile_pictures/{filename}"
                pic_path = pilot['profile_picture_path']
                filename = pic_path.split('/')[-1] if '/' in pic_path else pic_path
                pilot_picture = f"/profile_pictures/{filename}"
            
            # Build observer data with profile picture
            observer_picture = None
            if observer and observer.get("profile_picture_path"):
                # Extract filename from "profile_pictures/{filename}"
                pic_path = observer['profile_picture_path']
                filename = pic_path.split('/')[-1] if '/' in pic_path else pic_path
                observer_picture = f"/profile_pictures/{filename}"
            
            pairing_data = {
                "id": pairing["id"],
                "pilot_name": pilot["name"] if pilot else "Unknown",
                "pilot_initials": get_initials(pilot["name"]) if pilot else "?",
                "pilot_picture": pilot_picture,
                "pilot_color": get_avatar_color(pilot["name"]) if pilot else "avatar-color-1",
                "observer_name": observer["name"] if observer else "Unknown",
                "observer_initials": get_initials(observer["name"]) if observer else "?",
                "observer_picture": observer_picture,
                "observer_color": get_avatar_color(observer["name"]) if observer else "avatar-color-2"
            }
            
            # Count active assignments for this pairing
            active_assignments = db.get_assignments_for_pairing(pairing["id"], completed=False)
            assigned_navs_count = len(active_assignments) if active_assignments else 0
        
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
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "member_name": user["name"],
            "is_coach": is_coach,
            "is_admin": is_admin,
            "pairing_info": pairing_data,
            "recent_results": recent_results,
            "assigned_navs_count": assigned_navs_count,
            "stats": None
        })

# Legacy redirects for backward compatibility
@app.get("/team")
async def team_redirect(request: Request):
    """Legacy redirect: /team -> /dashboard"""
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Show password reset page. Issue 13."""
    must_reset = request.session.get("must_reset_password", False)
    user = request.session.get("user")
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "user": user,
        "must_reset": must_reset
    })

@app.post("/reset-password")
async def reset_password(
    request: Request,
    password: str = Form(...),
    password_confirm: str = Form(...)
):
    """Handle password reset. Issue 13."""
    user = request.session.get("user")
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    if password != password_confirm:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "user": user,
            "error": "Passwords do not match"
        })
    
    if len(password) < 8:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "user": user,
            "error": "Password must be at least 8 characters"
        })
    
    try:
        # Update password
        password_hash = auth.hash_password(password)
        db.update_user(user["user_id"], password_hash=password_hash, must_reset_password=0)
        
        # Clear the must_reset flag
        request.session.pop("must_reset_password", None)
        
        logger.info(f"User {user['email']} successfully reset their password")
        
        # Show success and redirect
        request.session["message"] = "Password reset successfully!"
        if user["is_coach"]:
            return RedirectResponse(url="/coach", status_code=303)
        else:
            return RedirectResponse(url="/team", status_code=303)
    except Exception as e:
        logger.error(f"Error resetting password for user {user['email']}: {e}")
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "user": user,
            "error": f"Error resetting password: {str(e)}"
        })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: dict = Depends(require_login)):
    """Display user profile page with picture upload."""
    user_data = db.get_user_by_id(user["user_id"])
    
    profile_picture = None
    if user_data and user_data.get("profile_picture_path"):
        pic_path = user_data['profile_picture_path']
        filename = pic_path.split('/')[-1] if '/' in pic_path else pic_path
        profile_picture = f"/profile_pictures/{filename}"
    
    return templates.TemplateResponse("team/profile.html", {
        "request": request,
        "member_name": user["name"],
        "user_email": user["email"],
        "user": user_data,
        "profile_picture": profile_picture,
        "initials": get_initials(user["name"]),
        "avatar_color": get_avatar_color(user["name"])
    })

@app.post("/profile/picture")
async def upload_profile_picture(
    request: Request,
    user: dict = Depends(require_login),
    profile_picture: Optional[UploadFile] = File(None)
):
    """Upload or update user's profile picture."""
    try:
        if not profile_picture or profile_picture.size == 0:
            return {"success": False, "message": "No file provided"}
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if profile_picture.size > max_size:
            return {"success": False, "message": "File too large (max 5MB)"}
        
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if profile_picture.content_type not in allowed_types:
            return {"success": False, "message": "Invalid file type. Allowed: JPG, PNG, GIF, WebP"}
        
        # Create profile_pictures directory if it doesn't exist
        profile_pics_dir = Path("data/profile_pictures")
        profile_pics_dir.mkdir(parents=True, exist_ok=True)
        
        # Read file content
        file_content = await profile_picture.read()
        
        # Generate filename: user_id_timestamp.ext
        from datetime import datetime as dt
        timestamp = int(dt.utcnow().timestamp())
        file_ext = profile_picture.filename.split('.')[-1].lower()
        filename = f"{user['user_id']}_{timestamp}.{file_ext}"
        
        # Save file
        file_path = profile_pics_dir / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Update database with new picture path
        relative_path = f"profile_pictures/{filename}"
        db.update_user(user["user_id"], profile_picture_path=relative_path)
        
        logger.info(f"Profile picture uploaded for user {user['user_id']}: {filename}")
        
        return {
            "success": True,
            "message": "Profile picture uploaded successfully",
            "path": f"/static/{relative_path}"
        }
    
    except Exception as e:
        logger.error(f"Error uploading profile picture for user {user['user_id']}: {e}")
        return {"success": False, "message": f"Error uploading file: {str(e)}"}

# ===== EMAIL MANAGEMENT ENDPOINTS =====

@app.get("/profile/emails")
async def get_profile_emails(user: dict = Depends(require_login)):
    """Get all email addresses for current user (primary + additional)."""
    try:
        all_emails = db.get_all_emails_for_user(user["user_id"])
        additional_emails = db.get_user_emails(user["user_id"])
        primary_email = user["email"]
        
        return {
            "success": True,
            "primary_email": primary_email,
            "additional_emails": additional_emails,
            "all_emails": all_emails
        }
    except Exception as e:
        logger.error(f"Error getting emails for user {user['user_id']}: {e}")
        return {"success": False, "message": f"Error retrieving emails: {str(e)}"}

@app.post("/profile/emails/add")
async def add_profile_email(user: dict = Depends(require_login), email: str = Form(...)):
    """Add a new email address for current user."""
    try:
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return {"success": False, "message": "Invalid email format"}
        
        # Check if email is the same as primary email
        if email.lower() == user["email"].lower():
            return {"success": False, "message": "This is already your primary email"}
        
        # Check if email already exists (for this user or another)
        if db.email_exists(email):
            return {"success": False, "message": "This email is already in use"}
        
        # Add the email
        if db.add_user_email(user["user_id"], email):
            return {"success": True, "message": f"Email {email} added successfully"}
        else:
            return {"success": False, "message": "Failed to add email"}
    
    except Exception as e:
        logger.error(f"Error adding email for user {user['user_id']}: {e}")
        return {"success": False, "message": f"Error adding email: {str(e)}"}

@app.post("/profile/emails/remove")
async def remove_profile_email(user: dict = Depends(require_login), email: str = Form(...)):
    """Remove an additional email address for current user."""
    try:
        # Check if trying to remove primary email
        if email.lower() == user["email"].lower():
            return {"success": False, "message": "Cannot remove your primary email"}
        
        # Remove the email
        if db.remove_user_email(user["user_id"], email):
            return {"success": True, "message": f"Email {email} removed successfully"}
        else:
            return {"success": False, "message": "Failed to remove email"}
    
    except Exception as e:
        logger.error(f"Error removing email for user {user['user_id']}: {e}")
        return {"success": False, "message": f"Error removing email: {str(e)}"}

@app.post("/profile/password")
async def change_password(
    request: Request,
    user: dict = Depends(require_login),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Change password for current user."""
    try:
        # Get user from database
        user_data = db.get_user_by_id(user["user_id"])
        
        if not user_data:
            return {"success": False, "message": "User not found"}
        
        # Verify current password
        if not auth.verify_password(current_password, user_data["password_hash"]):
            return {"success": False, "message": "Current password is incorrect"}
        
        # Check new password confirmation
        if new_password != confirm_password:
            return {"success": False, "message": "New passwords do not match"}
        
        # Check password length
        if len(new_password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters"}
        
        # Check if new password is same as current
        if auth.verify_password(new_password, user_data["password_hash"]):
            return {"success": False, "message": "New password must be different from current password"}
        
        # Hash and update password
        password_hash = auth.hash_password(new_password)
        db.update_user(user["user_id"], password_hash=password_hash)
        
        logger.info(f"User {user['email']} successfully changed their password")
        return {"success": True, "message": "Password changed successfully"}
    
    except Exception as e:
        logger.error(f"Error changing password for user {user['user_id']}: {e}")
        return {"success": False, "message": f"Error changing password: {str(e)}"}

@app.get("/team", response_class=HTMLResponse)
async def team_dashboard(request: Request, user: dict = Depends(require_competitor)):
    """Team member main dashboard."""
    # Get pairing info
    pairing = db.get_active_pairing_for_member(user["user_id"])
    pairing_data = None
    
    if pairing:
        pilot = db.get_user_by_id(pairing["pilot_id"])
        observer = db.get_user_by_id(pairing["safety_observer_id"])
        
        # Build pilot data with profile picture
        pilot_picture = None
        if pilot and pilot.get("profile_picture_path"):
            pic_path = pilot['profile_picture_path']
            filename = pic_path.split('/')[-1] if '/' in pic_path else pic_path
            pilot_picture = f"/profile_pictures/{filename}"
        
        # Build observer data with profile picture
        observer_picture = None
        if observer and observer.get("profile_picture_path"):
            pic_path = observer['profile_picture_path']
            filename = pic_path.split('/')[-1] if '/' in pic_path else pic_path
            observer_picture = f"/profile_pictures/{filename}"
        
        pairing_data = {
            "id": pairing["id"],
            "pilot_name": pilot["name"] if pilot else "Unknown",
            "pilot_initials": get_initials(pilot["name"]) if pilot else "?",
            "pilot_picture": pilot_picture,
            "pilot_color": get_avatar_color(pilot["name"]) if pilot else "avatar-color-1",
            "observer_name": observer["name"] if observer else "Unknown",
            "observer_initials": get_initials(observer["name"]) if observer else "?",
            "observer_picture": observer_picture,
            "observer_color": get_avatar_color(observer["name"]) if observer else "avatar-color-2"
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
async def prenav_form(request: Request, user: dict = Depends(require_login)):
    """Display pre-flight form. Coaches can select pairing, competitors use their own.
    
    Query parameters:
    - nav_id: Pre-select a NAV and skip the selection page (for assignment workflow)
    """
    is_coach = user.get("is_coach", False)
    is_admin = user.get("is_admin", False)
    
    # Get nav_id from query params if provided (from assignment workflow)
    nav_id = request.query_params.get('nav_id', None)
    
    navs = db.list_navs()
    
    # Add checkpoint counts to navs
    for nav in navs:
        checkpoints = db.get_checkpoints(nav["id"])
        nav["checkpoints"] = checkpoints
    
    # Handle pairing selection
    pairing_data = None
    pairings_for_dropdown = []
    
    if is_coach or is_admin:
        # Coaches can submit for any pairing
        all_pairings = db.list_pairings(active_only=True)
        for p in all_pairings:
            pilot = db.get_user_by_id(p["pilot_id"])
            observer = db.get_user_by_id(p["safety_observer_id"])
            pairings_for_dropdown.append({
                "id": p["id"],
                "display_name": f"{pilot['name'] if pilot else 'Unknown'} / {observer['name'] if observer else 'Unknown'}"
            })
    else:
        # Competitors use their own pairing
        pairing = db.get_active_pairing_for_member(user["user_id"])
        if pairing:
            pilot = db.get_user_by_id(pairing["pilot_id"])
            observer = db.get_user_by_id(pairing["safety_observer_id"])
            pairing_data = {
                "id": pairing["id"],
                "pilot_name": pilot["name"] if pilot else "Unknown",
                "observer_name": observer["name"] if observer else "Unknown"
            }
    
    return templates.TemplateResponse("team/prenav.html", {
        "request": request,
        "navs": navs,
        "pairing": pairing_data,
        "pairings_for_dropdown": pairings_for_dropdown,
        "is_coach": is_coach,
        "is_admin": is_admin,
        "member_name": user["name"],
        "nav_id": nav_id  # Pass nav_id to template for pre-selection
    })

@app.post("/prenav")
async def submit_prenav(
    request: Request,
    user: dict = Depends(require_login),
    nav_id: int = Form(...),
    leg_times_str: str = Form(...),
    total_time_str: str = Form(...),
    fuel_estimate: float = Form(...),
    pairing_id: int = Form(None)
):
    """Submit pre-flight plan. Coaches can specify pairing_id, competitors use their own."""
    try:
        is_coach = user.get("is_coach", False)
        is_admin = user.get("is_admin", False)
        
        logger.info(f"Prenav submission from user {user['user_id']}: nav_id={nav_id}, fuel_estimate={fuel_estimate}")
        
        # Get pairing based on role
        if is_coach or is_admin:
            # Coaches must specify pairing_id
            if not pairing_id:
                logger.error(f"Coach {user['user_id']} did not specify pairing_id")
                raise HTTPException(status_code=400, detail="Please select a pairing")
            pairing = db.get_pairing(pairing_id)
            if not pairing:
                logger.error(f"Pairing {pairing_id} not found")
                raise HTTPException(status_code=400, detail="Invalid pairing selected")
        else:
            # Competitors use their own pairing
            pairing = db.get_active_pairing_for_member(user["user_id"])
            if not pairing:
                logger.error(f"No active pairing found for competitor {user['user_id']}")
                raise HTTPException(status_code=400, detail="No active pairing found")
            pairing_id = pairing["id"]
        
        # Verify user is in pairing (pilot or observer) or allow coach to submit
        if not (is_coach or is_admin) and user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
            logger.error(f"User {user['user_id']} is not in pairing {pairing['id']} (pilot_id={pairing['pilot_id']}, observer_id={pairing['safety_observer_id']})")
            raise HTTPException(status_code=403, detail="You are not authorized to submit pre-flight plan for this pairing")
        
        # Parse times - Issue 16: leg_times_str is now JSON array of seconds, total_time_str is seconds
        try:
            leg_times_list = json.loads(leg_times_str)
            # leg_times_list is already in seconds (from HH:MM:SS conversion in frontend)
            leg_times = [int(t) for t in leg_times_list]
            total_time = int(total_time_str)
            logger.info(f"Parsed times: {leg_times} (total={total_time}s)")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing times: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid time format: {str(e)}")
        
        # Create prenav without token (v0.4.0)
        # token and expires_at are optional; status='open' is used instead
        prenav_id = db.create_prenav(
            pairing_id=pairing["id"],
            pilot_id=user["user_id"],
            nav_id=nav_id,
            leg_times=leg_times,
            total_time=total_time,
            fuel_estimate=fuel_estimate
        )
        
        logger.info(f"Created prenav: ID={prenav_id} (status=open, no token)")
        
        # Get NAV name
        nav = db.get_nav(nav_id)
        
        # Get pairing details for email
        pilot = db.get_user_by_id(pairing["pilot_id"])
        observer = db.get_user_by_id(pairing["safety_observer_id"])
        
        # Send emails to both pilot and observer (including additional emails)
        pilot_emails = db.get_all_emails_for_user(pairing["pilot_id"]) if pilot else []
        observer_emails = db.get_all_emails_for_user(pairing["safety_observer_id"]) if observer else []
        
        try:
            if pilot_emails:
                await email_service.send_prenav_confirmation(
                    team_emails=pilot_emails,
                    team_name=pilot["name"],
                    nav_name=nav["name"],
                    submission_date=datetime.utcnow().isoformat(),
                    pilot_name=pilot["name"],
                    observer_name=observer["name"] if observer else "Unknown"
                )
            
            if observer_emails:
                await email_service.send_prenav_confirmation(
                    team_emails=observer_emails,
                    team_name=observer["name"],
                    nav_name=nav["name"],
                    submission_date=datetime.utcnow().isoformat(),
                    pilot_name=pilot["name"] if pilot else "Unknown",
                    observer_name=observer["name"]
                )
        except Exception as email_err:
            logger.warning(f"Email send failed (non-critical): {email_err}")
        
        logger.info(f"Prenav submitted successfully, redirecting to confirmation")
        # Redirect to confirmation page with prenav ID instead of token
        return RedirectResponse(url=f"/prenav_confirmation?prenav_id={prenav_id}", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting prenav: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/prenav_confirmation", response_class=HTMLResponse)
async def prenav_confirmation(request: Request, user: dict = Depends(require_login), prenav_id: int = None):
    """Display pre-flight confirmation page. v0.4.0: Use prenav_id instead of token."""
    prenav = db.get_prenav(prenav_id) if prenav_id else None
    if not prenav:
        raise HTTPException(status_code=400, detail="Invalid prenav ID")
    
    # Get nav and pairing details for confirmation
    nav = db.get_nav(prenav["nav_id"])
    pairing = db.get_pairing(prenav["pairing_id"])
    pilot = db.get_user_by_id(pairing["pilot_id"]) if pairing else None
    observer = db.get_user_by_id(pairing["safety_observer_id"]) if pairing else None
    
    # Get assignment associated with this prenav
    assignment = db.get_assignment_by_prenav(prenav_id)
    assignment_id = assignment["id"] if assignment else None
    
    # Use submitted_at from prenav (matching the schema)
    created_at = datetime.fromisoformat(prenav.get("submitted_at") or datetime.utcnow().isoformat())
    
    return templates.TemplateResponse("team/prenav_confirmation.html", {
        "request": request,
        "prenav_id": prenav_id,
        "prenav": prenav,
        "nav_name": nav["name"] if nav else "Unknown",
        "pilot_name": pilot["name"] if pilot else "Unknown",
        "observer_name": observer["name"] if observer else "Unknown",
        "created_at": created_at.strftime("%Y-%m-%d %H:%M UTC"),
        "member_name": user["name"],
        "assignment_id": assignment_id
    })

@app.get("/flight/select", response_class=HTMLResponse)
async def flight_select_page(request: Request, user: dict = Depends(require_login)):
    """Display selection page with table of open pre-flight submissions. v0.4.2
    
    Query parameters:
    - assignment_id: If provided, find the corresponding prenav and redirect directly to /flight
                     (for assignment workflow - skip the selection page)
    """
    is_coach = user.get("is_coach", False)
    is_admin = user.get("is_admin", False)
    
    # Handle assignment_id - redirect directly to flight form if it's for the assignment
    assignment_id = request.query_params.get('assignment_id', None)
    if assignment_id:
        try:
            assignment_id = int(assignment_id)
            # Get the assignment to find nav_id
            assignment = db.get_assignment(assignment_id)
            if assignment:
                # Find the prenav for this assignment's NAV
                open_prenavs = db.get_open_prenav_submissions(
                    user_id=user["user_id"],
                    is_coach=(is_coach or is_admin),
                    nav_id=assignment["nav_id"]  # Filter by this assignment's NAV
                )
                
                # If there's exactly one prenav for this NAV, redirect to it
                if open_prenavs and len(open_prenavs) == 1:
                    prenav_id = open_prenavs[0]['id']
                    logger.info(f"Redirecting assignment {assignment_id} to prenav {prenav_id}")
                    return RedirectResponse(url=f"/flight?prenav_id={prenav_id}", status_code=303)
                # If multiple prenavs, continue to selection page
                # If no prenavs, continue to selection page (show error there)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Invalid assignment_id in /flight/select: {e}")
            # Continue to normal selection page
    
    # Get open prenav submissions (filtered by role)
    open_prenavs = db.get_open_prenav_submissions(
        user_id=user["user_id"],
        is_coach=(is_coach or is_admin)
    )
    
    # Format total_time for display
    for prenav in open_prenavs:
        total_time = prenav.get('total_time', 0)
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)
        prenav['total_time_display'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get message from query param if present
    message = request.query_params.get('message', None)
    
    return templates.TemplateResponse("team/flight_select.html", {
        "request": request,
        "member_name": user["name"],
        "open_prenavs": open_prenavs,
        "is_admin": is_admin,
        "is_coach": is_coach,
        "message": message
    })

@app.get("/flight", response_class=HTMLResponse)
async def flight_form(request: Request, user: dict = Depends(require_login)):
    """Display post-flight form with pre-selected submission. v0.4.2: Accepts ?prenav_id=X"""
    is_coach = user.get("is_coach", False)
    is_admin = user.get("is_admin", False)
    
    # Get prenav_id from query params if provided
    prenav_id = request.query_params.get('prenav_id', None)
    selected_prenav = None
    
    if prenav_id:
        try:
            prenav_id = int(prenav_id)
            selected_prenav = db.get_prenav_by_id(prenav_id)
            
            if not selected_prenav:
                return templates.TemplateResponse("team/flight.html", {
                    "request": request,
                    "member_name": user["name"],
                    "selected_prenav": None,
                    "start_gates": [],
                    "error": f"Pre-flight submission #{prenav_id} not found.",
                    "is_admin": is_admin,
                    "is_coach": is_coach
                })
            
            # Validate permissions (competitor must be in pairing)
            if not is_coach and not is_admin:
                if user["user_id"] not in [selected_prenav['pilot_id'], selected_prenav['safety_observer_id']]:
                    raise HTTPException(status_code=403, detail="You don't have permission to score this submission")
        
        except ValueError:
            return templates.TemplateResponse("team/flight.html", {
                "request": request,
                "member_name": user["name"],
                "selected_prenav": None,
                "start_gates": [],
                "error": "Invalid prenav_id parameter.",
                "is_admin": is_admin,
                "is_coach": is_coach
            })
    
    # Get all start gates
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
        "selected_prenav": selected_prenav,
        "is_coach": is_coach,
        "is_admin": is_admin,
        "member_name": user["name"],
        "error": None
    })

@app.post("/flight", response_class=HTMLResponse)
async def submit_flight(
    request: Request,
    user: dict = Depends(require_login),
    prenav_id: int = Form(...),
    actual_fuel: Optional[float] = Form(None),  # Make optional for backward compatibility
    actual_fuel_gallons: Optional[str] = Form(None),  # Accept as string initially
    actual_fuel_tenths: Optional[str] = Form(None),   # Accept as string initially
    secrets_checkpoint: int = Form(...),
    secrets_enroute: int = Form(...),
    start_gate_id: int = Form(...),
    gpx_file: UploadFile = File(...)
):
    """Submit post-flight GPX and process scoring. v0.4.6: Fixed actual_fuel field handling."""
    is_coach = user.get("is_coach", False)
    is_admin = user.get("is_admin", False)
    
    # Log all form parameters for debugging
    logger.info(f"POST /flight FORM DEBUG:")
    logger.info(f"  prenav_id={prenav_id} (type: {type(prenav_id).__name__})")
    logger.info(f"  actual_fuel={actual_fuel} (type: {type(actual_fuel).__name__ if actual_fuel is not None else 'None'})")
    logger.info(f"  actual_fuel_gallons={actual_fuel_gallons!r} (type: {type(actual_fuel_gallons).__name__ if actual_fuel_gallons is not None else 'None'})")
    logger.info(f"  actual_fuel_tenths={actual_fuel_tenths!r} (type: {type(actual_fuel_tenths).__name__ if actual_fuel_tenths is not None else 'None'})")
    logger.info(f"  secrets_checkpoint={secrets_checkpoint} (type: {type(secrets_checkpoint).__name__})")
    logger.info(f"  secrets_enroute={secrets_enroute} (type: {type(secrets_enroute).__name__})")
    logger.info(f"  start_gate_id={start_gate_id} (type: {type(start_gate_id).__name__})")
    logger.info(f"  gpx_file={gpx_file} (type: {type(gpx_file).__name__})")
    logger.info(f"POST /flight: User {user['user_id']} ({user['name']}) submitting prenav_id={prenav_id}. is_coach={is_coach}, is_admin={is_admin}")
    
    error = None
    try:
        # Handle actual_fuel - either from combined hidden field or from separate inputs
        if actual_fuel is None:
            # Try to combine gallons and tenths if provided
            if actual_fuel_gallons and actual_fuel_tenths:
                try:
                    gallons = float(actual_fuel_gallons.strip())
                    tenths = float(actual_fuel_tenths.strip())
                    actual_fuel = gallons + (tenths / 10.0)
                    logger.info(f"Combined fuel from separate inputs: {actual_fuel_gallons} gallons + {actual_fuel_tenths} tenths = {actual_fuel}")
                except (ValueError, AttributeError) as e:
                    error = f"Invalid fuel values. Please enter valid numbers for gallons and tenths. Error: {str(e)}"
                    logger.error(f"POST /flight: Error parsing fuel values - {error}")
            else:
                error = "Please enter actual fuel burn (gallons and tenths)"
                logger.error(f"POST /flight: Missing fuel values - gallons={actual_fuel_gallons!r}, tenths={actual_fuel_tenths!r}")
        
        # Validate fuel value
        if not error and (actual_fuel is None or actual_fuel < 0):
            error = f"Invalid fuel value: {actual_fuel}. Please enter a positive number."
            logger.error(f"POST /flight: Invalid fuel value - {error}")
        # Validate prenav_id
        prenav = db.get_prenav(prenav_id)
        logger.debug(f"POST /flight: prenav_id={prenav_id}, found={prenav is not None}")
        if not prenav:
            error = "Invalid prenav submission"
        
        # Check if prenav is still open
        if not error and prenav.get("status") != "open":
            error = f"This submission has already been scored or archived"
        
        # Get pairing
        if not error:
            pairing = db.get_pairing(prenav["pairing_id"])
            if not pairing:
                error = "Pairing not found"
        
        # Verify user is authorized
        if not error:
            # Coaches/admins can submit for any pairing, competitors must be part of the pairing
            if not (is_coach or is_admin):
                if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
                    error = "You are not authorized to score this submission"
                    logger.warning(f"Authorization failed: competitor {user['user_id']} not in pairing {pairing['id']}")
                else:
                    logger.info(f"Authorization passed: competitor {user['user_id']} is in pairing {pairing['id']}")
            else:
                logger.info(f"Authorization passed: user {user['user_id']} is coach/admin, can submit for any pairing")
        
        # Save GPX file
        if not error:
            try:
                gpx_storage = Path(config["storage"]["gpx_uploads"])
                gpx_storage.mkdir(parents=True, exist_ok=True)
                
                gpx_filename = f"gpx_{pairing['id']}_{prenav['nav_id']}_{int(datetime.utcnow().timestamp())}.gpx"
                gpx_path = gpx_storage / gpx_filename
                
                gpx_content = await gpx_file.read()
                if not gpx_content:
                    error = "GPX file is empty"
                else:
                    gpx_path.write_bytes(gpx_content)
            except Exception as e:
                error = f"Failed to save GPX file: {str(e)}"
        
        # Parse GPX
        if not error:
            try:
                track_points = parse_gpx(gpx_content)
                if not track_points:
                    error = "No track points found in GPX file"
            except Exception as e:
                error = f"Failed to parse GPX file: {str(e)}"
        
        # Get NAV and checkpoints
        if not error:
            nav = db.get_nav(prenav["nav_id"])
            checkpoints = nav["checkpoints"]
            
            # Validate leg_times count matches checkpoints
            if len(prenav.get("leg_times", [])) != len(checkpoints):
                error = f"Leg times count mismatch: expected {len(checkpoints)}, got {len(prenav.get('leg_times', []))}. This may indicate a data integrity issue."
                logger.error(f"POST /flight: {error} for prenav_id={prenav_id}")
        
        # Get start gate
        if not error:
            start_gate = db.get_start_gate(start_gate_id)
            if not start_gate:
                error = "Invalid start gate"
        
        # Detect start gate crossing
        if not error:
            try:
                start_crossing, start_distance = scoring_engine.detect_start_gate_crossing(
                    track_points, start_gate
                )
                
                if not start_crossing:
                    error = "Could not detect start gate crossing. Please check your GPX file and try again."
            except Exception as e:
                error = f"Error detecting start gate: {str(e)}"
        
        # Score checkpoints
        checkpoint_results = []
        if not error:
            try:
                previous_point = start_crossing
                previous_time = start_crossing["time"]
                
                for i, checkpoint in enumerate(checkpoints):
                    timing_point, distance_nm, method, within_025 = scoring_engine.find_checkpoint_crossing(
                        track_points, checkpoint, previous_point, previous_time
                    )
                    
                    if not timing_point:
                        logger.error(f"Could not find crossing for checkpoint {checkpoint['name']}")
                        continue
                    
                    # Calculate leg score
                    estimated_time = prenav["leg_times"][i]
                    logger.debug(f"Checkpoint {i} ({checkpoint['name']}): estimated_time={estimated_time}s, distance={distance_nm}nm, method={method}")
                    actual_time = (timing_point["time"] - previous_time).total_seconds()
                    
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
                    previous_time = timing_point["time"]
            except Exception as e:
                error = f"Error scoring checkpoints: {str(e)}"
        
        # If no error, proceed with scoring
        if not error:
            try:
                logger.info(f"POST /flight: Beginning flight scoring...")
                logger.info(f"  prenav: {prenav}")
                logger.info(f"  checkpoint_results count: {len(checkpoint_results)}")
                logger.info(f"  checkpoint_results: {checkpoint_results}")
                
                # Calculate total scores
                # Sum of individual leg penalties
                leg_penalties = sum(cp["leg_score"] for cp in checkpoint_results)
                
                # Calculate actual total time from checkpoint crossings
                actual_total_time = sum(cp["actual_time"] for cp in checkpoint_results)
                
                # Get estimated total time from prenav (user input, may have math errors)
                estimated_total_time = prenav["total_time"]
                
                # Calculate total time penalty (separate component)
                # Sign convention: negative = faster than estimated (actual < estimated)
                total_time_deviation = actual_total_time - estimated_total_time
                total_time_penalty = abs(total_time_deviation) * config["scoring"].get("timing_penalty_per_second", 1.0)
                
                # Total timing score = leg penalties + total time penalty (both are timing components)
                total_time_score = leg_penalties + total_time_penalty
                
                # Calculate total off-course penalty
                total_off_course = sum(cp["off_course_penalty"] for cp in checkpoint_results)
                
                logger.info(f"Timing breakdown: leg_penalties={leg_penalties:.1f}, total_time_penalty={total_time_penalty:.1f}, total={total_time_score:.1f}")
                
                fuel_penalty = scoring_engine.calculate_fuel_penalty(
                    prenav["fuel_estimate"], actual_fuel
                )
                
                # Calculate fuel error percentage
                fuel_error_pct = 0
                if prenav["fuel_estimate"] > 0:
                    fuel_error_pct = ((actual_fuel - prenav["fuel_estimate"]) / prenav["fuel_estimate"]) * 100
                
                checkpoint_secrets_penalty, enroute_secrets_penalty = scoring_engine.calculate_secrets_penalty(
                    secrets_checkpoint, secrets_enroute
                )
                
                checkpoint_scores = [(cp["leg_score"], cp["off_course_penalty"]) for cp in checkpoint_results]
                
                # Pass ONLY the total_time_penalty (not leg_penalties + total_time_penalty)
                # checkpoint_scores already contains the leg_score from each checkpoint
                overall_score = scoring_engine.calculate_overall_score(
                    checkpoint_scores,
                    total_time_penalty,  # Changed from total_time_score to total_time_penalty
                    fuel_penalty,
                    checkpoint_secrets_penalty,
                    enroute_secrets_penalty
                )
                
                # Generate enhanced PDF with maps
                pdf_storage = Path(config["storage"]["pdf_reports"])
                pdf_storage.mkdir(parents=True, exist_ok=True)
                
                # Generate full route map
                timestamp = int(datetime.utcnow().timestamp())
                full_route_map_filename = f"route_map_{pairing['id']}_{prenav['nav_id']}_{timestamp}.png"
                full_route_map_path = pdf_storage / full_route_map_filename
                
                generate_full_route_map(track_points, start_gate, checkpoints, full_route_map_path)
                
                # Generate checkpoint detail maps
                checkpoint_maps_paths = []
                for i, checkpoint in enumerate(checkpoints):
                    map_filename = f"checkpoint_map_{i+1}_{pairing['id']}_{prenav['nav_id']}_{timestamp}.png"
                    map_path = pdf_storage / map_filename
                    # Determine previous checkpoint or start gate
                    prev_checkpoint = checkpoints[i-1] if i > 0 else None
                    generate_checkpoint_detail_map(
                        track_points, checkpoint, i+1, map_path,
                        start_gate=start_gate,
                        previous_checkpoint=prev_checkpoint
                    )
                    checkpoint_maps_paths.append(map_path)
                
                # Generate PDF
                pdf_filename = f"result_{pairing['id']}_{prenav['nav_id']}_{timestamp}.pdf"
                pdf_path = pdf_storage / pdf_filename
                
                # Get pairing member names
                pilot = db.get_user_by_id(pairing["pilot_id"])
                observer = db.get_user_by_id(pairing["safety_observer_id"])
                
                pairing_display = {
                    "pilot_name": pilot["name"] if pilot else "Unknown",
                    "observer_name": observer["name"] if observer else "Unknown"
                }
                
                result_data_for_pdf = {
                    "overall_score": overall_score,
                    "total_time_score": total_time_score,
                    "leg_penalties": leg_penalties,
                    "total_time_penalty": total_time_penalty,
                    "total_time_deviation": total_time_deviation,
                    "estimated_total_time": estimated_total_time,
                    "actual_total_time": actual_total_time,
                    "total_off_course": total_off_course,
                    "fuel_penalty": fuel_penalty,
                    "fuel_error_pct": fuel_error_pct,
                    "estimated_fuel_burn": prenav["fuel_estimate"],
                    "actual_fuel_burn": actual_fuel,
                    "checkpoint_secrets_penalty": checkpoint_secrets_penalty,
                    "enroute_secrets_penalty": enroute_secrets_penalty,
                    "secrets_missed_checkpoint": secrets_checkpoint,
                    "secrets_missed_enroute": secrets_enroute,
                    "checkpoint_results": checkpoint_results,
                    "scored_at": datetime.utcnow().isoformat(),
                    "flight_started_at": prenav.get("submitted_at", datetime.utcnow().isoformat())
                }
                
                # Call enhanced PDF generator
                generate_enhanced_pdf_report(
                    result_data_for_pdf, nav, pairing_display,
                    start_gate, checkpoints, track_points,
                    full_route_map_path, checkpoint_maps_paths,
                    pdf_path
                )
                
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
                    checkpoint_results=checkpoint_results,
                    leg_penalties=leg_penalties,
                    total_time_penalty=total_time_penalty,
                    total_time_deviation=total_time_deviation,
                    estimated_total_time=estimated_total_time,
                    actual_total_time=actual_total_time,
                    total_off_course=total_off_course,
                    fuel_error_pct=fuel_error_pct,
                    estimated_fuel_burn=prenav["fuel_estimate"],
                    checkpoint_radius=config["scoring"]["off_course"].get("checkpoint_radius_nm", 0.25)
                )
                
                # Mark prenav as scored (v0.4.0)
                db.mark_prenav_scored(prenav["id"])
                logger.info(f"Marked prenav {prenav['id']} as scored")
                
                # Mark assignment as complete if exists (Item 37)
                assignment = db.get_assignment_by_prenav(prenav["id"])
                if assignment:
                    db.mark_assignment_complete(assignment["id"])
                    logger.info(f"Marked assignment {assignment['id']} as completed (NAV {prenav['nav_id']}, Pairing {pairing['id']})")
                
                # Update with PDF filename
                from app.database import Database as DB
                with db.get_connection() as conn:
                    conn.execute(
                        "UPDATE flight_results SET pdf_filename = ? WHERE id = ?",
                        (pdf_filename, result_id)
                    )
                
                # Send emails (including additional emails)
                pilot_emails = db.get_all_emails_for_user(pilot["id"]) if pilot else []
                observer_emails = db.get_all_emails_for_user(observer["id"]) if observer else []
                
                team_name = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Team"
                
                if pilot_emails:
                    try:
                        await email_service.send_results_notification(
                            team_emails=pilot_emails,
                            team_name=pilot["name"],
                            nav_name=nav["name"],
                            overall_score=overall_score,
                            pdf_filename=pdf_filename
                        )
                    except Exception as email_err:
                        logger.warning(f"Failed to send email to pilot: {email_err}")
                
                if observer_emails:
                    try:
                        await email_service.send_results_notification(
                            team_emails=observer_emails,
                            team_name=observer["name"],
                            nav_name=nav["name"],
                            overall_score=overall_score,
                            pdf_filename=pdf_filename
                        )
                    except Exception as email_err:
                        logger.warning(f"Failed to send email to observer: {email_err}")
                
                # Redirect to results page
                logger.info(f"POST /flight: Successfully scored prenav_id={prenav_id}, result_id={result_id}, overall_score={overall_score:.1f}. Redirecting to results page.")
                return RedirectResponse(url=f"/results/{result_id}", status_code=303)
            except Exception as e:
                import traceback
                logger.error(f"Error processing flight: {e}", exc_info=True)
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception args: {e.args}")
                logger.error(f"Exception message: {str(e)}")
                logger.error(f"Exception traceback: {traceback.format_exc()}")
                
                # Log detailed context
                logger.error(f"Context at error:")
                logger.error(f"  prenav_id: {prenav_id}")
                logger.error(f"  prenav: {prenav}")
                logger.error(f"  nav_id: {prenav.get('nav_id') if prenav else None}")
                logger.error(f"  checkpoint_results count: {len(checkpoint_results) if checkpoint_results else 0}")
                if checkpoint_results:
                    logger.error(f"  first checkpoint: {checkpoint_results[0] if len(checkpoint_results) > 0 else None}")
                
                # Provide better error message for common issues
                error_str = str(e)
                if "NOT NULL" in error_str:
                    error = f"Database error: Missing required data. Please check all form fields are filled correctly."
                elif "FOREIGN KEY" in error_str:
                    error = f"Database error: Invalid reference. Please try again or contact support."
                elif len(error_str) == 0 or error_str == "None":
                    error = "An unknown error occurred during flight scoring. Please try again or contact support."
                else:
                    error = f"Error processing flight: {error_str}"
    
    except Exception as e:
        logger.error(f"Unexpected error in submit_flight: {e}", exc_info=True)
        error = f"An unexpected error occurred: {str(e)}"
    
    # If there was an error, render the form with the error message
    if error:
        logger.warning(f"POST /flight: Error processing prenav_id={prenav_id} for user {user['user_id']}: {error}")
        navs = db.list_navs()
        gates = []
        for nav in navs:
            nav_gates = db.get_start_gates(nav["airport_id"])
            for gate in nav_gates:
                if gate not in gates:
                    gates.append(gate)
        
        # Get the prenav that was submitted to redisplay the form
        submitted_prenav = db.get_prenav(prenav_id) if prenav_id else None
        
        # If we have the prenav, format it for redisplay
        selected_prenav_display = None
        if submitted_prenav:
            # Format total_time for display
            total_time = submitted_prenav.get('total_time', 0)
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            seconds = int(total_time % 60)
            total_time_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Get pairing names
            pairing = db.get_pairing(submitted_prenav["pairing_id"])
            pilot = db.get_user_by_id(pairing["pilot_id"]) if pairing else None
            observer = db.get_user_by_id(pairing["safety_observer_id"]) if pairing else None
            
            selected_prenav_display = {
                "id": submitted_prenav["id"],
                "submitted_at_display": submitted_prenav.get("submitted_at_display", "Unknown"),
                "nav_name": submitted_prenav.get("nav_name", "Unknown"),
                "pilot_name": pilot["name"] if pilot else "Unknown",
                "observer_name": observer["name"] if observer else "Unknown",
                "total_time_display": total_time_display,
                "fuel_estimate": submitted_prenav.get("fuel_estimate", 0),
            }
        
        return templates.TemplateResponse("team/flight.html", {
            "request": request,
            "start_gates": gates,
            "selected_prenav": selected_prenav_display,  # Pass the original prenav to redisplay the form
            "is_coach": is_coach,
            "is_admin": is_admin,
            "member_name": user["name"],
            "error": error
        })

@app.get("/flight/delete/{prenav_id}/confirm", response_class=HTMLResponse)
async def confirm_delete_prenav(request: Request, prenav_id: int, user: dict = Depends(require_admin)):
    """Show confirmation page for pre-flight submission deletion."""
    prenav = db.get_prenav_by_id(prenav_id)
    if not prenav:
        raise HTTPException(status_code=404, detail="Pre-flight submission not found")
    
    # Check if already scored
    if prenav['status'] == 'scored':
        raise HTTPException(status_code=400, detail="Cannot delete scored submission")
    
    return templates.TemplateResponse("coach/delete_confirm.html", {
        "request": request,
        "warning_message": "Are you sure you want to delete this pre-flight submission?",
        "cascade_info": f"Submission: {prenav['submitted_at_display']} - {prenav['nav_name']} - {prenav['pilot_name']} + {prenav['observer_name']}",
        "confirm_url": f"/flight/delete/{prenav_id}",
        "cancel_url": "/flight/select"
    })

@app.post("/flight/delete/{prenav_id}")
async def delete_prenav_submission(prenav_id: int, user: dict = Depends(require_admin)):
    """Delete a pre-flight submission (admin only). v0.4.3"""
    try:
        # Check if submission exists
        prenav = db.get_prenav_by_id(prenav_id)
        if not prenav:
            raise HTTPException(status_code=404, detail="Pre-flight submission not found")
        
        # Check if already scored (don't allow deletion)
        if prenav['status'] == 'scored':
            raise HTTPException(status_code=400, detail="Cannot delete scored submission")
        
        # Delete
        db.delete_prenav_submission(prenav_id)
        logger.info(f"Admin {user['user_id']} deleted prenav submission {prenav_id}")
        
        return RedirectResponse(url="/flight/select", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prenav {prenav_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete submission")

@app.get("/results/{result_id}", response_class=HTMLResponse)
async def view_result(request: Request, result_id: int, user: dict = Depends(require_login)):
    """View specific result. Issue 18: Better error handling and logging."""
    try:
        logger.info(f"Fetching result {result_id} for user {user['user_id']}")
        
        result = db.get_flight_result(result_id)
        if not result:
            logger.warning(f"Result {result_id} not found")
            raise HTTPException(status_code=404, detail="Result not found")
        
        # Verify user is part of pairing (unless coach/admin)
        is_coach = user.get("is_coach", False)
        is_admin = user.get("is_admin", False)
        
        pairing = db.get_pairing(result["pairing_id"])
        if not (is_coach or is_admin):  # Only enforce pairing check for competitors
            if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
                logger.warning(f"Competitor user {user['user_id']} not authorized to view result {result_id}")
                raise HTTPException(status_code=403, detail="Not authorized to view this result")
        else:
            logger.info(f"Coach/admin user {user['user_id']} accessing result {result_id}")
        
        # Get NAV
        nav = db.get_nav(result["nav_id"])
        
        # Get pairing member names for display
        pairing_info = None
        if pairing:
            pilot = db.get_user_by_id(pairing["pilot_id"])
            observer = db.get_user_by_id(pairing["safety_observer_id"])
            pairing_info = {
                "pilot_name": pilot["name"] if pilot else "Unknown",
                "observer_name": observer["name"] if observer else "Unknown"
            }
        
        # Get prenav - use fallback from result if prenav is missing
        prenav = db.get_prenav(result["prenav_id"])
        if not prenav:
            logger.warning(f"Prenav {result['prenav_id']} not found for result {result_id}, using defaults from result")
            # Create minimal prenav object from result data to allow viewing
            prenav = {
                "fuel_estimate": result.get("estimated_fuel_burn", 0),
                "total_time": result.get("estimated_total_time", 0)
            }
        
        # Build result display
        result_display = {
            "id": result["id"],
            "overall_score": result["overall_score"],
            "checkpoint_results": result["checkpoint_results"],
            "total_time_score": result.get("leg_penalties", 0) + result.get("total_time_penalty", 0),
            "total_deviation": sum(abs(cp["deviation"]) for cp in result["checkpoint_results"]),
            "fuel_penalty": 0,  # Calculate from prenav and actual
            "checkpoint_secrets_penalty": result["secrets_missed_checkpoint"] * config["scoring"]["secrets"]["checkpoint_penalty"],
            "enroute_secrets_penalty": result["secrets_missed_enroute"] * config["scoring"]["secrets"]["enroute_penalty"],
            "estimated_fuel_burn": result.get("estimated_fuel_burn") or prenav["fuel_estimate"],
            "actual_fuel_burn": result["actual_fuel"],
            "pdf_filename": result.get("pdf_filename"),
            "scored_at": result["scored_at"],
            "flight_started_at": prenav.get("submitted_at"),  # Time when start gate was triggered
            # New fields from v0.4.8
            "leg_penalties": result.get("leg_penalties", 0),
            "total_time_penalty": result.get("total_time_penalty", 0),
            "total_time_deviation": result.get("total_time_deviation", 0),
            "estimated_total_time": result.get("estimated_total_time") or prenav.get("total_time", 0),
            "actual_total_time": result.get("actual_total_time", 0),
            "total_off_course": result.get("total_off_course", 0),
            "fuel_error_pct": result.get("fuel_error_pct", 0),
            "checkpoint_radius": result.get("checkpoint_radius", 0.25),
            "secrets_missed_checkpoint": result["secrets_missed_checkpoint"],
            "secrets_missed_enroute": result["secrets_missed_enroute"]
        }
        
        # Recalculate fuel penalty
        fuel_penalty = scoring_engine.calculate_fuel_penalty(
            prenav["fuel_estimate"], result["actual_fuel"]
        )
        result_display["fuel_penalty"] = fuel_penalty
        
        logger.debug(f"Successfully loaded result {result_id} for user {user['user_id']}")
        
        return templates.TemplateResponse("team/results.html", {
            "request": request,
            "result": result_display,
            "nav": nav,
            "pairing": pairing_info,
            "member_name": user["name"]
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing result {result_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error loading result: {str(e)}")

@app.get("/results/{result_id}/pdf")
async def download_pdf(result_id: int, user: dict = Depends(require_login)):
    """Download PDF report. v0.4.5: Allow coaches/admins to download any PDF."""
    result = db.get_flight_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Verify authorization (coaches/admins can download any, competitors only their own)
    is_coach = user.get("is_coach", False)
    is_admin = user.get("is_admin", False)
    
    if not (is_coach or is_admin):
        pairing = db.get_pairing(result["pairing_id"])
        if user["user_id"] not in [pairing["pilot_id"], pairing["safety_observer_id"]]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    if not result.get("pdf_filename"):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_path = Path(config["storage"]["pdf_reports"]) / result["pdf_filename"]
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=result["pdf_filename"])

@app.get("/coach/navs/{nav_id}/pdf")
async def download_nav_pdf(nav_id: int, user: dict = Depends(require_login)):
    """Download NAV packet PDF. Available to all authenticated users."""
    try:
        nav = db.get_nav(nav_id)
        if not nav:
            raise HTTPException(status_code=404, detail="NAV not found")
        
        # Check if pdf_path is set
        pdf_path_value = nav.get("pdf_path")
        if not pdf_path_value:
            raise HTTPException(status_code=404, detail="NAV packet PDF not available")
        
        # Build full path - try multiple possible locations
        pdf_path = Path(pdf_path_value)
        
        # If it's a relative path, try to resolve it
        if not pdf_path.is_absolute():
            # Try: data/{pdf_path_value}
            candidate1 = Path("data") / pdf_path_value
            # Try: {pdf_path_value} as-is
            candidate2 = Path(pdf_path_value)
            # Try: data/nav_packets/{filename} (in case pdf_path_value is just the filename)
            pdf_filename = Path(pdf_path_value).name
            candidate3 = Path("data/nav_packets") / pdf_filename
            
            candidates = [candidate1, candidate2, candidate3]
            pdf_path = None
            
            for candidate in candidates:
                if candidate.exists():
                    pdf_path = candidate
                    logger.info(f"Found NAV PDF at: {pdf_path}")
                    break
            
            if not pdf_path:
                logger.error(f"NAV PDF not found in any of: {candidates}")
                raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
        # Verify file exists
        if not pdf_path.exists():
            logger.error(f"NAV PDF file not found: {pdf_path}")
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
        # Return the PDF file
        filename = f"{nav['name']}_NAV_Packet.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading NAV PDF for nav_id {nav_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading PDF: {str(e)}")

@app.get("/results", response_class=HTMLResponse)
async def list_results(request: Request, user: dict = Depends(require_login)):
    """List results - competitors see only their results, coaches/admins see all. Issue 18: Better error handling."""
    try:
        is_coach = user.get("is_coach", False)
        is_admin = user.get("is_admin", False)
        
        logger.info(f"Fetching results for user {user['user_id']}")
        
        if is_coach or is_admin:
            # Coaches/Admins see ALL results
            results = db.list_flight_results()
        else:
            # Competitors see only their own results
            pairings = db.list_pairings_for_member(user["user_id"], active_only=False)
            pairing_ids = [p["id"] for p in pairings]
            
            results = []
            for pairing_id in pairing_ids:
                pairing_results = db.list_flight_results(pairing_id=pairing_id)
                results.extend(pairing_results)
        
        logger.info(f"Found {len(results)} results")
        
        # Sort by date descending
        results.sort(key=lambda r: r["scored_at"], reverse=True)
        
        # Enhance with NAV and pairing names
        for result in results:
            nav = db.get_nav(result["nav_id"])
            result["nav_name"] = nav["name"] if nav else "Unknown"
            
            pairing = db.get_pairing(result["pairing_id"])
            if pairing:
                pilot = db.get_user_by_id(pairing["pilot_id"])
                observer = db.get_user_by_id(pairing["safety_observer_id"])
                result["team_name"] = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Unknown"
        
        logger.debug(f"Successfully loaded results page for user {user['user_id']}")
        
        # Use coach template for coaches/admins, team template for competitors
        template_name = "coach/results.html" if (is_coach or is_admin) else "team/results_list.html"
        
        return templates.TemplateResponse(template_name, {
            "request": request,
            "results": results,
            "member_name": user["name"]
        })
    except Exception as e:
        logger.error(f"Results page error for user {user['user_id']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error loading results: {str(e)}")

# ===== COACH ROUTES =====

@app.get("/coach", response_class=HTMLResponse)
async def coach_dashboard(request: Request, user: dict = Depends(require_coach)):
    """Coach main dashboard."""
    members = db.list_users(filter_type="approved")
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
            pilot = db.get_user_by_id(pairing["pilot_id"])
            observer = db.get_user_by_id(pairing["safety_observer_id"])
            result["team_name"] = f"{pilot['name']} / {observer['name']}" if pilot and observer else "Unknown"
    
    # Calculate stats - ensure they're integers
    total_users_count = len(members) if members else 0
    active_pairings_count = len(pairings) if pairings else 0
    recent_results_count = len(results) if results else 0
    
    return templates.TemplateResponse("coach/dashboard.html", {
        "request": request,
        "is_admin": user.get("is_admin", False),
        "pending_count": pending_count,
        "stats": {
            "total_users": total_users_count,
            "active_pairings": active_pairings_count,
            "recent_results": recent_results_count
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
            pilot = db.get_user_by_id(pairing["pilot_id"])
            observer = db.get_user_by_id(pairing["safety_observer_id"])
            result["pilot_name"] = pilot["name"] if pilot else "Unknown"
            result["observer_name"] = observer["name"] if observer else "Unknown"
        
        # Calculate component scores
        prenav = db.get_prenav(result["prenav_id"])
        if prenav:
            fuel_penalty = scoring_engine.calculate_fuel_penalty(
                prenav["fuel_estimate"], result["actual_fuel"]
            )
            result["fuel_penalty"] = fuel_penalty
            result["total_time_score"] = result.get("leg_penalties", 0) + result.get("total_time_penalty", 0)
    
    # Get all pairings and NAVs for filter dropdowns
    pairings = db.list_pairings(active_only=False)
    for pairing in pairings:
        pilot = db.get_user_by_id(pairing["pilot_id"])
        observer = db.get_user_by_id(pairing["safety_observer_id"])
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
    try:
        result = db.get_flight_result(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        
        nav = db.get_nav(result["nav_id"])
        
        # Get pairing member names for display
        pairing_info = None
        pairing = db.get_pairing(result["pairing_id"])
        if pairing:
            pilot = db.get_user_by_id(pairing["pilot_id"])
            observer = db.get_user_by_id(pairing["safety_observer_id"])
            pairing_info = {
                "pilot_name": pilot["name"] if pilot else "Unknown",
                "observer_name": observer["name"] if observer else "Unknown"
            }
        
        prenav = db.get_prenav(result["prenav_id"])
        
        # Handle missing prenav gracefully
        if not prenav:
            logger.warning(f"Prenav {result['prenav_id']} not found for result {result_id}, using defaults from result")
            prenav = {
                "fuel_estimate": result.get("estimated_fuel_burn", 0),
                "total_time": result.get("estimated_total_time", 0)
            }
        
        result_display = {
            "id": result["id"],
            "overall_score": result["overall_score"],
            "checkpoint_results": result["checkpoint_results"],
            "total_time_score": result.get("leg_penalties", 0) + result.get("total_time_penalty", 0),
            "total_deviation": sum(abs(cp["deviation"]) for cp in result["checkpoint_results"]),
            "fuel_penalty": scoring_engine.calculate_fuel_penalty(prenav["fuel_estimate"], result["actual_fuel"]),
            "checkpoint_secrets_penalty": result["secrets_missed_checkpoint"] * config["scoring"]["secrets"]["checkpoint_penalty"],
            "enroute_secrets_penalty": result["secrets_missed_enroute"] * config["scoring"]["secrets"]["enroute_penalty"],
            "estimated_fuel_burn": result.get("estimated_fuel_burn") or prenav["fuel_estimate"],
            "actual_fuel_burn": result["actual_fuel"],
            "pdf_filename": result.get("pdf_filename"),
            "scored_at": result["scored_at"],
            "flight_started_at": prenav.get("submitted_at"),  # Time when start gate was triggered
            # New fields from v0.4.8
            "leg_penalties": result.get("leg_penalties", 0),
            "total_time_penalty": result.get("total_time_penalty", 0),
            "total_time_deviation": result.get("total_time_deviation", 0),
            "estimated_total_time": result.get("estimated_total_time") or prenav.get("total_time", 0),
            "actual_total_time": result.get("actual_total_time", 0),
            "total_off_course": result.get("total_off_course", 0),
            "fuel_error_pct": result.get("fuel_error_pct", 0),
            "checkpoint_radius": result.get("checkpoint_radius", 0.25),
            "secrets_missed_checkpoint": result["secrets_missed_checkpoint"],
            "secrets_missed_enroute": result["secrets_missed_enroute"]
        }
        
        return templates.TemplateResponse("team/results.html", {
            "request": request,
            "result": result_display,
            "nav": nav,
            "pairing": pairing_info,
            "member_name": "Coach",
            "dashboard_url": "/coach"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing result {result_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error loading result: {str(e)}")

@app.get("/coach/results/{result_id}/delete")
async def coach_delete_result(result_id: int, user: dict = Depends(require_admin)):
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

@app.get("/coach/users", response_class=HTMLResponse)
async def coach_users(request: Request, user: dict = Depends(require_coach), filter_type: str = "all"):
    """User management - coaches and admins can view and manage users."""
    users = db.list_users(filter_type=filter_type)
    is_admin = user.get("is_admin", False)
    return templates.TemplateResponse("coach/users.html", {
        "request": request,
        "users": users,
        "current_filter": filter_type,
        "is_admin": is_admin
    })

@app.post("/coach/users/update")
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

@app.post("/coach/users/edit")
async def edit_user(
    request: Request,
    user: dict = Depends(require_admin)
):
    """Edit user details (name, email, password, profile picture). Admin only. Issue 13: Support force_reset flag. Items 31, 32: Profile picture admin."""
    try:
        form_data = await request.form()
        user_id = form_data.get("user_id")
        name = form_data.get("name")
        email = form_data.get("email")
        password = form_data.get("password")
        force_reset = form_data.get("force_reset") == "1"  # Issue 13
        can_modify_profile_picture = form_data.get("can_modify_profile_picture") == "1"  # Item 32
        profile_picture = form_data.get("profile_picture")  # Item 31
        
        if not user_id or not name or not email:
            return {"success": False, "message": "Missing required fields"}
        
        # Build update dict
        updates = {
            "name": name,
            "email": email,
            "username": email,  # Update username to match email
            "can_modify_profile_picture": 1 if can_modify_profile_picture else 0  # Item 32
        }
        
        # Only update password if provided
        if password:
            updates["password_hash"] = auth.hash_password(password)
        
        # Issue 13: Handle force_reset flag
        if force_reset:
            updates["must_reset_password"] = 1
        
        # Item 31: Handle profile picture upload
        if profile_picture and hasattr(profile_picture, 'file'):
            # Validate file
            max_size = 5 * 1024 * 1024  # 5MB
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
            
            if profile_picture.size > max_size:
                return {"success": False, "message": "Profile picture must be under 5MB"}
            
            if profile_picture.content_type not in allowed_types:
                return {"success": False, "message": "Profile picture must be JPG, PNG, or GIF"}
            
            # Save the file
            profile_pics_dir = Path("data/profile_pictures")
            profile_pics_dir.mkdir(parents=True, exist_ok=True)
            
            file_content = await profile_picture.read()
            file_ext = profile_picture.filename.split('.')[-1].lower()
            filename = f"user_{user_id}_{int(datetime.now().timestamp())}.{file_ext}"
            file_path = profile_pics_dir / filename
            
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            relative_path = f"profile_pictures/{filename}"
            updates["profile_picture_path"] = relative_path
            logger.info(f"Admin uploaded profile picture for user {user_id}: {relative_path}")
        
        # Update user
        success = db.update_user(int(user_id), **updates)
        
        if success:
            log_msg = f"User {user_id} edited: name={name}, email={email}"
            if force_reset:
                log_msg += ", force_reset=true"
            if can_modify_profile_picture:
                log_msg += ", can_modify_profile_picture=true"
            else:
                log_msg += ", can_modify_profile_picture=false"
            logger.info(log_msg)
            return {"success": True, "message": "User updated successfully"}
        else:
            return {"success": False, "message": "User not found"}
    
    except Exception as e:
        logger.error(f"Error editing user: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/users/{user_id}/remove-profile-picture")
async def remove_profile_picture_admin(
    user_id: int,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Remove a user's profile picture. Admin only. Item 31."""
    try:
        # Get user to check if they have a profile picture
        target_user = db.get_user_by_id(user_id)
        if not target_user:
            return {"success": False, "message": "User not found"}
        
        # Remove the profile picture file if it exists
        if target_user.get("profile_picture_path"):
            picture_path = Path("static") / target_user["profile_picture_path"]
            if picture_path.exists():
                picture_path.unlink()
                logger.info(f"Deleted profile picture file: {picture_path}")
        
        # Update database
        success = db.update_user(user_id, profile_picture_path=None)
        
        if success:
            logger.info(f"Admin removed profile picture for user {user_id}")
            return {"success": True, "message": "Profile picture removed successfully"}
        else:
            return {"success": False, "message": "Failed to update database"}
    
    except Exception as e:
        logger.error(f"Error removing profile picture for user {user_id}: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/users/{user_id}/delete")
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
            return RedirectResponse(url="/coach/users?message=User deleted", status_code=303)
        else:
            return RedirectResponse(url="/coach/users?error=User not found", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return RedirectResponse(url=f"/coach/users?error={str(e)}", status_code=303)

@app.post("/coach/users")
async def coach_create_member(
    request: Request,
    user: dict = Depends(require_admin),
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    force_reset: str = Form(default="0")
):
    """Create new user (unified users table). Admin-created users are pre-approved."""
    try:
        if not password:
            return RedirectResponse(url="/coach/users?error=Password is required", status_code=303)
        
        # Determine if user should be forced to reset password
        must_reset_password = force_reset == "1"
        logger.info(f"Coach creating user: {email}, force_reset checkbox value='{force_reset}', must_reset_password={must_reset_password}")
        
        # Create user in unified users table - admin-created users are pre-approved
        password_hash = auth.hash_password(password)
        user_id = db.create_user(
            username=email,  # Email is now the login credential
            password_hash=password_hash,
            email=email,
            name=name,
            is_coach=False,
            is_admin=False,
            is_approved=1,  # Admin-created users are pre-approved
            email_verified=True,  # Coach-created accounts have verified email
            must_reset_password=must_reset_password  # Respect the checkbox value
        )
        logger.info(f"New user created (pre-approved): {email} (ID: {user_id}, must_reset_password={must_reset_password})")
        return RedirectResponse(url="/coach/users?message=User created and approved", status_code=303)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return RedirectResponse(url=f"/coach/users?error={str(e)}", status_code=303)

@app.post("/coach/users/bulk")
async def coach_bulk_members(
    request: Request,
    user: dict = Depends(require_admin),
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
        
        return RedirectResponse(url=f"/coach/users?message=Created {count} members", status_code=303)
    except Exception as e:
        logger.error(f"Error bulk creating members: {e}")
        return RedirectResponse(url=f"/coach/users?error={str(e)}", status_code=303)

@app.get("/coach/users/{member_id}/deactivate")
async def coach_deactivate_user(member_id: int, user: dict = Depends(require_admin)):
    """Deactivate user."""
    db.update_user(member_id, is_active=0)
    return RedirectResponse(url="/coach/users", status_code=303)

@app.get("/coach/users/{member_id}/activate")
async def coach_activate_user(member_id: int, user: dict = Depends(require_admin)):
    """Activate user."""
    db.update_user(member_id, is_active=1)
    return RedirectResponse(url="/coach/users", status_code=303)

@app.post("/coach/users/{user_id}/approve")
async def approve_user_ajax(
    user_id: int,
    user: dict = Depends(require_admin)
):
    """Approve a user via AJAX. Admin only. Issue 19."""
    try:
        success = db.update_user(user_id, **{"is_approved": 1})
        if success:
            logger.info(f"User {user_id} approved by admin {user.get('user_id')}")
            return {"success": True, "message": "User approved"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        logger.error(f"Error approving user: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/users/{user_id}/deny")
async def deny_user_ajax(
    user_id: int,
    user: dict = Depends(require_admin)
):
    """Deny a user via AJAX. Admin only. Issue 19."""
    try:
        success = db.update_user(user_id, **{"is_approved": 0})
        if success:
            logger.info(f"User {user_id} denied by admin {user.get('user_id')}")
            return {"success": True, "message": "User denied"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        logger.error(f"Error denying user: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/users/{user_id}/force-password-reset")
async def force_password_reset(
    user_id: int,
    user: dict = Depends(require_admin)
):
    """Force user to reset password on next login. Admin only."""
    try:
        success = db.update_user(user_id, must_reset_password=1)
        if success:
            logger.info(f"Password reset forced for user {user_id} by admin {user.get('user_id')}")
            return {"success": True, "message": "User will be required to reset password on next login"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        logger.error(f"Error forcing password reset: {e}")
        return {"success": False, "message": str(e)}

@app.get("/coach/pairings", response_class=HTMLResponse)
async def coach_pairings(request: Request, user: dict = Depends(require_coach), message: Optional[str] = None, error: Optional[str] = None):
    """Pairing management. Issue 15: Names populated from DB join. Issue 24: Filter dropdowns."""
    # Get only available users for dropdown population (exclude coaches, admins, and already-paired users)
    users = db.get_available_pairing_users()
    active_pairings = db.list_pairings(active_only=True)
    inactive_pairings = [p for p in db.list_pairings(active_only=False) if not p["is_active"]]
    
    # Names are already populated by list_pairings via JOIN
    is_admin = user.get("is_admin", False)
    
    # Get message/error from query params
    message = request.query_params.get("message", message)
    error = request.query_params.get("error", error)
    
    return templates.TemplateResponse("coach/pairings.html", {
        "request": request,
        "members": users,
        "active_pairings": active_pairings,
        "inactive_pairings": inactive_pairings,
        "is_admin": is_admin,
        "message": message,
        "error": error
    })

@app.post("/coach/pairings")
async def coach_create_pairing(
    request: Request,
    user: dict = Depends(require_admin),
    pilot_id: int = Form(...),
    safety_observer_id: int = Form(...)
):
    """Create pairing. Issue 20: Returns JSON for AJAX, redirect for form submission."""
    try:
        pairing_id = db.create_pairing(pilot_id, safety_observer_id)
        # Check if it's an AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            return {"success": True, "pairing_id": pairing_id}
        else:
            return RedirectResponse(url="/coach/pairings?message=Pairing created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating pairing: {e}")
        error_msg = str(e)
        # Check if it's an AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            return {"success": False, "detail": error_msg}
        else:
            return RedirectResponse(url=f"/coach/pairings?error={error_msg}", status_code=303)

@app.get("/coach/pairings/{pairing_id}/break")
async def coach_break_pairing(pairing_id: int, user: dict = Depends(require_admin)):
    """Break pairing."""
    db.break_pairing(pairing_id)
    return RedirectResponse(url="/coach/pairings?message=Pairing broken", status_code=303)

@app.get("/coach/pairings/{pairing_id}/reactivate")
async def coach_reactivate_pairing(pairing_id: int, user: dict = Depends(require_admin)):
    """Reactivate pairing."""
    db.update_pairing(pairing_id, is_active=1)
    return RedirectResponse(url="/coach/pairings?message=Pairing reactivated", status_code=303)

@app.get("/coach/pairings/{pairing_id}/delete")
async def coach_delete_pairing(pairing_id: int, user: dict = Depends(require_admin)):
    """Delete pairing."""
    db.delete_pairing(pairing_id)
    return RedirectResponse(url="/coach/pairings?message=Pairing deleted", status_code=303)

@app.get("/coach/navs", response_class=HTMLResponse)
async def coach_navs(request: Request, user: dict = Depends(require_coach)):
    """NAV management - redirect to airports page. Item 36."""
    return RedirectResponse(url="/coach/navs/airports", status_code=303)

@app.get("/coach/navs/airports", response_class=HTMLResponse)
async def coach_manage_airports(request: Request, user: dict = Depends(require_coach)):
    """Airports selection page - redesigned navigation flow. Item 36."""
    airports = db.list_airports()
    is_admin = user.get("is_admin", False)
    
    # Add counts for each airport
    for airport in airports:
        navs = db.list_navs_by_airport(airport["id"])
        gates = db.get_start_gates(airport["id"])
        airport["nav_count"] = len(navs)
        airport["gate_count"] = len(gates)
    
    return templates.TemplateResponse("coach/navs_airports.html", {
        "request": request,
        "airports": airports,
        "is_admin": is_admin,
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@app.post("/coach/navs/airports/create")
async def coach_create_airport(
    request: Request,
    user: dict = Depends(require_admin),
    code: str = Form(...)
):
    """Create airport - Item 36."""
    try:
        code = code.strip().upper()
        if not code:
            raise ValueError("Airport code cannot be empty")
        airport_id = db.create_airport(code)
        logger.info(f"Created airport {airport_id} with code {code}")
        return RedirectResponse(url="/coach/navs/airports?message=Airport created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating airport: {e}")
        return RedirectResponse(url=f"/coach/navs/airports?error={str(e)}", status_code=303)

@app.get("/coach/navs/airport/{airport_id}", response_class=HTMLResponse)
async def coach_airport_detail(airport_id: int, request: Request, user: dict = Depends(require_coach)):
    """Airport detail page showing gates and NAVs. Item 36."""
    airport = db.get_airport(airport_id)
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    
    gates = db.get_start_gates(airport_id)
    navs = db.list_navs_by_airport(airport_id)
    
    # Add checkpoint counts to NAVs
    for nav in navs:
        checkpoints = db.get_checkpoints(nav["id"])
        nav["checkpoint_count"] = len(checkpoints)
    
    # Sort NAVs alphabetically
    navs.sort(key=lambda x: x["name"])
    
    return templates.TemplateResponse("coach/navs_airport_detail.html", {
        "request": request,
        "user": user,
        "airport": airport,
        "airport_id": airport_id,
        "airport_code": airport["code"],
        "gates": gates,
        "navs": navs,
        "is_admin": user.get("is_admin", False),
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@app.get("/coach/navs/route/{nav_id}", response_class=HTMLResponse)
async def coach_route_detail(nav_id: int, request: Request, user: dict = Depends(require_coach)):
    """Route detail page for checkpoint management with drag-and-drop. Item 36."""
    nav = db.get_nav(nav_id)
    if not nav:
        raise HTTPException(status_code=404, detail="NAV not found")
    
    airport = db.get_airport(nav["airport_id"])
    checkpoints = db.get_checkpoints(nav_id)
    
    return templates.TemplateResponse("coach/navs_route_detail.html", {
        "request": request,
        "user": user,
        "nav": nav,
        "airport_id": nav["airport_id"],
        "airport_code": airport["code"] if airport else "Unknown",
        "checkpoints": checkpoints,
        "is_admin": user.get("is_admin", False),
        "message": request.query_params.get("message"),
        "error": request.query_params.get("error")
    })

@app.post("/coach/navs/{nav_id}/upload-pdf")
async def upload_nav_pdf(nav_id: int, request: Request, user: dict = Depends(require_admin), pdf_file: UploadFile = File(...)):
    """Upload or replace NAV PDF packet."""
    try:
        nav = db.get_nav(nav_id)
        if not nav:
            raise HTTPException(status_code=404, detail="NAV not found")
        
        # Validate PDF file
        if not pdf_file.filename.lower().endswith('.pdf'):
            return {"success": False, "message": "Only PDF files are allowed"}
        
        max_size = 50 * 1024 * 1024  # 50MB
        content = await pdf_file.read()
        if len(content) > max_size:
            return {"success": False, "message": "PDF file must be under 50MB"}
        
        # Create storage directory
        pdf_storage = Path(config["storage"].get("nav_packets", "data/nav_packets"))
        pdf_storage.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(datetime.utcnow().timestamp())
        pdf_filename = f"nav_{nav_id}_{timestamp}.pdf"
        pdf_path = pdf_storage / pdf_filename
        
        # Delete old PDF if exists
        if nav.get("pdf_path"):
            old_path = Path(nav["pdf_path"])
            if old_path.exists():
                old_path.unlink()
        
        # Save new PDF
        pdf_path.write_bytes(content)
        
        # Update database
        relative_path = f"nav_packets/{pdf_filename}"
        db.update_nav_pdf(nav_id, relative_path)
        
        logger.info(f"NAV {nav_id} PDF uploaded: {pdf_filename}")
        return {"success": True, "message": "PDF uploaded successfully", "filename": pdf_filename}
    except Exception as e:
        logger.error(f"Error uploading NAV PDF: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/navs/{nav_id}/delete-pdf")
async def delete_nav_pdf(nav_id: int, user: dict = Depends(require_admin)):
    """Delete NAV PDF packet."""
    try:
        nav = db.get_nav(nav_id)
        if not nav:
            raise HTTPException(status_code=404, detail="NAV not found")
        
        # Delete file if exists
        if nav.get("pdf_path"):
            pdf_path = Path(nav["pdf_path"])
            if pdf_path.exists():
                pdf_path.unlink()
        
        # Update database
        db.delete_nav_pdf(nav_id)
        
        logger.info(f"NAV {nav_id} PDF deleted")
        return {"success": True, "message": "PDF deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting NAV PDF: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/navs/airports")
async def coach_create_airport(
    request: Request,
    user: dict = Depends(require_admin),
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

@app.get("/coach/navs/airports/{airport_id}/delete-confirm", response_class=HTMLResponse)
async def confirm_delete_airport(request: Request, airport_id: int, user: dict = Depends(require_admin)):
    """Show confirmation page for airport deletion."""
    airport = db.get_airport(airport_id)
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    
    return templates.TemplateResponse("coach/delete_confirm.html", {
        "request": request,
        "warning_message": f"Are you sure you want to delete airport {airport['code']}?",
        "cascade_info": "This will permanently delete all associated start gates and NAV routes.",
        "confirm_url": f"/coach/navs/airports/{airport_id}/delete",
        "cancel_url": "/coach/navs/airports"
    })

@app.post("/coach/navs/airports/{airport_id}/delete")
async def coach_delete_airport(airport_id: int, user: dict = Depends(require_admin)):
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
    is_admin = user.get("is_admin", False)
    return templates.TemplateResponse("coach/navs_gates.html", {
        "request": request,
        "airport": airport,
        "gates": gates,
        "is_admin": is_admin
    })

@app.post("/coach/navs/gates/create")
async def coach_create_gate(
    request: Request,
    user: dict = Depends(require_admin),
    airport_id: int = Form(...),
    name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...)
):
    """Create start gate - Item 36."""
    try:
        gate_id = db.create_start_gate(airport_id, name, lat, lon)
        logger.info(f"Created start gate {gate_id} for airport {airport_id}")
        return RedirectResponse(url=f"/coach/navs/airport/{airport_id}?message=Gate created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating gate: {e}")
        return RedirectResponse(url=f"/coach/navs/airport/{airport_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/gates/{gate_id}/delete-confirm", response_class=HTMLResponse)
async def confirm_delete_gate(request: Request, gate_id: int, user: dict = Depends(require_admin)):
    """Show confirmation page for gate deletion."""
    gate = db.get_start_gate(gate_id)
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    airport_id = gate["airport_id"]
    
    return templates.TemplateResponse("coach/delete_confirm.html", {
        "request": request,
        "warning_message": f"Are you sure you want to delete gate {gate['name']}?",
        "cascade_info": None,
        "confirm_url": f"/coach/navs/gates/{gate_id}/delete",
        "cancel_url": f"/coach/navs/gates/{airport_id}"
    })

@app.post("/coach/navs/gates/{gate_id}/delete")
async def coach_delete_gate(gate_id: int, user: dict = Depends(require_admin)):
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
    is_admin = user.get("is_admin", False)
    
    # Enhance navs with airport name and checkpoint count
    for nav in navs:
        airport = db.get_airport(nav["airport_id"])
        nav["airport_code"] = airport["code"] if airport else "Unknown"
        nav["checkpoints_count"] = len(db.get_checkpoints(nav["id"]))
    
    return templates.TemplateResponse("coach/navs_routes.html", {
        "request": request,
        "airports": airports,
        "navs": navs,
        "is_admin": is_admin
    })

@app.post("/coach/navs/routes/create")
async def coach_create_route(
    request: Request,
    user: dict = Depends(require_admin),
    name: str = Form(...),
    airport_id: int = Form(...)
):
    """Create NAV route - Item 36."""
    try:
        name = name.strip()
        if not name:
            raise ValueError("Route name cannot be empty")
        nav_id = db.create_nav(name, airport_id)
        logger.info(f"Created NAV route {nav_id} for airport {airport_id}")
        return RedirectResponse(url=f"/coach/navs/airport/{airport_id}?message=NAV route created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating route: {e}")
        return RedirectResponse(url=f"/coach/navs/airport/{airport_id}?error={str(e)}", status_code=303)

@app.get("/coach/navs/routes/{nav_id}/delete-confirm", response_class=HTMLResponse)
async def confirm_delete_route(request: Request, nav_id: int, user: dict = Depends(require_admin)):
    """Show confirmation page for NAV route deletion."""
    nav = db.get_nav(nav_id)
    if not nav:
        raise HTTPException(status_code=404, detail="NAV route not found")
    
    return templates.TemplateResponse("coach/delete_confirm.html", {
        "request": request,
        "warning_message": f"Are you sure you want to delete NAV route '{nav['name']}'?",
        "cascade_info": "This will permanently delete all checkpoints and secrets for this route.",
        "confirm_url": f"/coach/navs/routes/{nav_id}/delete",
        "cancel_url": "/coach/navs/routes"
    })

@app.post("/coach/navs/routes/{nav_id}/delete")
async def coach_delete_route(nav_id: int, user: dict = Depends(require_admin)):
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
    is_admin = user.get("is_admin", False)
    return templates.TemplateResponse("coach/navs_checkpoints.html", {
        "request": request,
        "nav": nav,
        "checkpoints": checkpoints,
        "is_admin": is_admin
    })

@app.post("/coach/navs/checkpoints")
async def coach_create_checkpoint(
    request: Request,
    user: dict = Depends(require_admin),
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

@app.get("/coach/navs/checkpoints/{checkpoint_id}/delete-confirm", response_class=HTMLResponse)
async def confirm_delete_checkpoint(request: Request, checkpoint_id: int, user: dict = Depends(require_admin)):
    """Show confirmation page for checkpoint deletion."""
    checkpoint = db.get_checkpoint(checkpoint_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    nav_id = checkpoint["nav_id"]
    
    return templates.TemplateResponse("coach/delete_confirm.html", {
        "request": request,
        "warning_message": f"Are you sure you want to delete checkpoint '{checkpoint['name']}'?",
        "cascade_info": None,
        "confirm_url": f"/coach/navs/checkpoints/{checkpoint_id}/delete",
        "cancel_url": f"/coach/navs/checkpoints/{nav_id}"
    })

@app.post("/coach/navs/checkpoints/{checkpoint_id}/delete")
async def coach_delete_checkpoint(checkpoint_id: int, user: dict = Depends(require_admin)):
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
    is_admin = user.get("is_admin", False)
    return templates.TemplateResponse("coach/navs_secrets.html", {
        "request": request,
        "nav": nav,
        "secrets": secrets,
        "is_admin": is_admin
    })

@app.post("/coach/navs/secrets")
async def coach_create_secret(
    request: Request,
    user: dict = Depends(require_admin),
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

@app.get("/coach/navs/secrets/{secret_id}/delete-confirm", response_class=HTMLResponse)
async def confirm_delete_secret(request: Request, secret_id: int, user: dict = Depends(require_admin)):
    """Show confirmation page for secret deletion."""
    secret = db.get_secret(secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    nav_id = secret["nav_id"]
    
    return templates.TemplateResponse("coach/delete_confirm.html", {
        "request": request,
        "warning_message": f"Are you sure you want to delete secret '{secret['name']}'?",
        "cascade_info": None,
        "confirm_url": f"/coach/navs/secrets/{secret_id}/delete",
        "cancel_url": f"/coach/navs/secrets/{nav_id}"
    })

@app.post("/coach/navs/secrets/{secret_id}/delete")
async def coach_delete_secret(secret_id: int, user: dict = Depends(require_admin)):
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
async def coach_config(request: Request, user: dict = Depends(require_admin), message: Optional[str] = None, error: Optional[str] = None):
    """View/edit config (admin only)."""
    config_data = config["scoring"]
    email_config = config.get("email", {})
    backup_config = config.get("backup", {})
    backup_status = backup_scheduler.get_status()
    
    # Get message/error from query params if not provided
    message = request.query_params.get("message", message)
    error = request.query_params.get("error", error)
    
    return templates.TemplateResponse("coach/config.html", {
        "request": request,
        "config": config_data,
        "email_config": email_config,
        "backup_config": backup_config,
        "backup_status": backup_status,
        "message": message,
        "error": error
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
        config_path = Path("data/config.yaml")
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
        config_path = Path("data/config.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump(config, default_flow_style=False))
        
        # Reload email service with new config
        global email_service
        email_service = EmailService(config["email"])
        
        return RedirectResponse(url="/coach/config?message=Email config updated successfully", status_code=303)
    except Exception as e:
        logger.error(f"Error updating email config: {e}")
        return RedirectResponse(url=f"/coach/config?error={str(e)}", status_code=303)

@app.post("/coach/test_smtp")
async def coach_test_smtp(request: Request, user: dict = Depends(require_admin)):
    """Test SMTP connection (admin only). Returns JSON."""
    try:
        success, message = await email_service.test_connection()
        return {"success": success, "message": message}
    except Exception as e:
        logger.error(f"Error testing SMTP: {e}")
        return {"success": False, "message": f"Error testing SMTP: {str(e)}"}

@app.post("/coach/config/backup")
async def coach_update_backup_config(
    request: Request,
    user: dict = Depends(require_admin),
    backup_enabled: Optional[str] = Form(None),
    backup_frequency_hours: int = Form(...),
    backup_retention_days: int = Form(...),
    backup_max_backups: int = Form(...),
    backup_path: str = Form(...)
):
    """Update backup configuration (admin only)."""
    try:
        # Update backup config
        config["backup"]["enabled"] = backup_enabled is not None
        config["backup"]["frequency_hours"] = backup_frequency_hours
        config["backup"]["retention_days"] = backup_retention_days
        config["backup"]["max_backups"] = backup_max_backups
        config["backup"]["backup_path"] = backup_path
        
        # Save to file
        config_path = Path("data/config.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump(config, default_flow_style=False))
        
        # Recreate backup scheduler with new config
        global backup_scheduler
        backup_scheduler = BackupScheduler(
            config.get("backup", {}),
            config["database"]["path"]
        )
        
        logger.info("Backup configuration updated")
        return RedirectResponse(url="/coach/config?message=Backup config updated successfully", status_code=303)
    except Exception as e:
        logger.error(f"Error updating backup config: {e}")
        return RedirectResponse(url=f"/coach/config?error={str(e)}", status_code=303)

@app.post("/coach/backup/run")
async def coach_run_backup(request: Request, user: dict = Depends(require_admin)):
    """Trigger manual backup (admin only). Returns JSON."""
    try:
        # Run backup in executor to avoid blocking
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, backup_scheduler.run_backup)
        
        if success:
            status = backup_scheduler.get_status()
            return {
                "success": True,
                "message": "Backup completed successfully",
                "backup_file": status.get("last_backup_file"),
                "last_backup": status.get("last_backup"),
                "total_backups": status.get("total_backups")
            }
        else:
            return {
                "success": False,
                "message": "Backup failed. Check logs for details."
            }
    except Exception as e:
        logger.error(f"Error running backup: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.get("/coach/backup/status")
async def coach_backup_status(request: Request, user: dict = Depends(require_admin)):
    """Get backup status (admin only). Returns JSON."""
    try:
        status = backup_scheduler.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

# ===== CHECKPOINT MANAGEMENT (Item 36) =====

@app.post("/coach/navs/checkpoints/create")
async def coach_create_checkpoint_new(
    request: Request,
    user: dict = Depends(require_admin),
    nav_id: int = Form(...),
    name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    sequence: int = Form(...)
):
    """Create checkpoint - Item 36."""
    try:
        checkpoint_id = db.create_checkpoint(nav_id, sequence, name, lat, lon)
        logger.info(f"Created checkpoint {checkpoint_id} for NAV {nav_id}")
        return RedirectResponse(url=f"/coach/navs/route/{nav_id}?message=Checkpoint created", status_code=303)
    except Exception as e:
        logger.error(f"Error creating checkpoint: {e}")
        return RedirectResponse(url=f"/coach/navs/route/{nav_id}?error={str(e)}", status_code=303)

@app.post("/coach/navs/checkpoints/{checkpoint_id}/update")
async def coach_update_checkpoint(
    checkpoint_id: int,
    request: Request,
    user: dict = Depends(require_admin),
    name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    sequence: int = Form(...)
):
    """Update checkpoint - Item 36."""
    try:
        # Get checkpoint to find nav_id
        checkpoint = db.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        nav_id = checkpoint["nav_id"]
        db.update_checkpoint(checkpoint_id, sequence, name, lat, lon)
        logger.info(f"Updated checkpoint {checkpoint_id}")
        return RedirectResponse(url=f"/coach/navs/route/{nav_id}?message=Checkpoint updated", status_code=303)
    except Exception as e:
        logger.error(f"Error updating checkpoint: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/navs/checkpoints/{checkpoint_id}/delete")
async def coach_delete_checkpoint_new(
    checkpoint_id: int,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Delete checkpoint - Item 36."""
    try:
        checkpoint = db.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        nav_id = checkpoint["nav_id"]
        db.delete_checkpoint(checkpoint_id)
        logger.info(f"Deleted checkpoint {checkpoint_id}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting checkpoint: {e}")
        return {"success": False, "message": str(e)}

@app.post("/coach/navs/checkpoints/reorder")
async def coach_reorder_checkpoints(request: Request, user: dict = Depends(require_admin)):
    """Reorder checkpoints - Item 36."""
    try:
        data = await request.json()
        nav_id = data.get("nav_id")
        checkpoints = data.get("checkpoints", [])
        
        # Update sequence for each checkpoint
        for cp in checkpoints:
            db.update_checkpoint_sequence(cp["id"], cp["sequence"])
        
        logger.info(f"Reordered {len(checkpoints)} checkpoints for NAV {nav_id}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error reordering checkpoints: {e}")
        return {"success": False, "message": str(e)}

# ===== NAV ASSIGNMENT ROUTES (Item 37) =====

@app.get("/coach/assignments", response_class=HTMLResponse)
async def coach_assignments(
    request: Request,
    user: dict = Depends(require_coach),
    status: str = "all",
    semester: str = None
):
    """View all NAV assignments. Coach/Admin only. Item 37."""
    try:
        # Get filter params
        completed = None if status == "all" else (status == "completed")
        
        # Get assignments
        assignments = db.get_all_assignments(completed=completed, semester=semester)
        
        # Get stats
        all_assignments = db.get_all_assignments()
        stats = {
            "total": len(all_assignments),
            "active": len([a for a in all_assignments if not a.get("completed_at")]),
            "completed": len([a for a in all_assignments if a.get("completed_at")])
        }
        
        # Get available pairings and NAVs for assignment form
        pairings = db.list_pairings(active_only=True)
        navs = db.list_navs()
        
        # Get unique semesters
        semesters = list(set([a.get("semester", "Spring 2026") for a in all_assignments]))
        semesters.sort(reverse=True)
        
        return templates.TemplateResponse("coach/assignments.html", {
            "request": request,
            "user": user,
            "assignments": assignments,
            "stats": stats,
            "pairings": pairings,
            "navs": navs,
            "semesters": semesters,
            "filter_status": status,
            "filter_semester": semester,
            "is_admin": user["is_admin"],
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error")
        })
    except Exception as e:
        logger.error(f"Error displaying assignments: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "user": user,
            "error": f"Error loading assignments: {str(e)}"
        })

@app.post("/coach/assignments/create")
async def coach_create_assignment(
    request: Request,
    user: dict = Depends(require_admin),
    nav_id: int = Form(...),
    semester: str = Form("Spring 2026"),
    notes: str = Form(None),
    pairing_ids: List[int] = Form(default=[])
):
    """Create new NAV assignment for one or more pairings. Admin only. Item 37."""
    try:
        # Handle backward compatibility: accept pairing_id if pairing_ids is empty
        form_data = await request.form()
        if not pairing_ids and 'pairing_id' in form_data:
            pairing_ids = [int(form_data['pairing_id'])]
        
        if not pairing_ids:
            return RedirectResponse(
                url="/coach/assignments?error=Please select at least one pairing",
                status_code=303
            )
        
        # Create assignments for each selected pairing
        successful_assignments = []
        failed_assignments = []
        duplicate_assignments = []
        
        # Get NAV details for email
        nav = db.get_nav(nav_id)
        nav_name = nav.get("name", "Unknown NAV") if nav else "Unknown NAV"
        
        for pairing_id in pairing_ids:
            # Check for duplicates
            if db.check_duplicate_assignment(nav_id, pairing_id, semester):
                duplicate_assignments.append(pairing_id)
                continue
            
            # Create assignment
            assignment_id = db.create_assignment(
                nav_id=nav_id,
                pairing_id=pairing_id,
                assigned_by=user["user_id"],
                semester=semester,
                notes=notes
            )
            
            if assignment_id:
                successful_assignments.append(pairing_id)
                logger.info(f"NAV assignment created: assignment_id={assignment_id} nav={nav_id} pairing={pairing_id} by user={user['user_id']}")
                
                # Send email notification to pilot and observer (fail gracefully if email fails)
                try:
                    pairing = db.get_pairing(pairing_id)
                    if pairing:
                        # Get full pairing details with names and emails via list_pairings
                        all_pairings = db.list_pairings(active_only=False)
                        pairing_details = next((p for p in all_pairings if p['id'] == pairing_id), None)
                        
                        if pairing_details:
                            await email_service.send_nav_assigned(
                                pilot_email=pairing_details.get("pilot_email", ""),
                                observer_email=pairing_details.get("observer_email", ""),
                                pilot_name=pairing_details.get("pilot_name", "Pilot"),
                                observer_name=pairing_details.get("observer_name", "Observer"),
                                nav_name=nav_name
                            )
                            logger.info(f"NAV assignment email sent for assignment_id={assignment_id}")
                except Exception as e:
                    # Log email error but don't fail the assignment creation
                    logger.error(f"Failed to send NAV assignment email for pairing {pairing_id}: {e}")
            else:
                failed_assignments.append(pairing_id)
        
        # Build response message
        if successful_assignments and not failed_assignments and not duplicate_assignments:
            if len(successful_assignments) == 1:
                message = "NAV assigned successfully to 1 pairing"
            else:
                message = f"NAV assigned successfully to {len(successful_assignments)} pairings"
            return RedirectResponse(
                url=f"/coach/assignments?message={message}",
                status_code=303
            )
        else:
            # Build detailed error/success message
            messages = []
            if successful_assignments:
                messages.append(f"{len(successful_assignments)} pairing(s) assigned")
            if duplicate_assignments:
                messages.append(f"{len(duplicate_assignments)} pairing(s) already have this NAV")
            if failed_assignments:
                messages.append(f"{len(failed_assignments)} pairing(s) failed to assign")
            
            message = "; ".join(messages)
            status = "error" if failed_assignments else "message"
            return RedirectResponse(
                url=f"/coach/assignments?{status}={message}",
                status_code=303
            )
    except Exception as e:
        logger.error(f"Error creating assignment: {e}")
        return RedirectResponse(
            url=f"/coach/assignments?error={str(e)}",
            status_code=303
        )

@app.post("/coach/assignments/{assignment_id}/delete")
async def coach_delete_assignment(
    assignment_id: int,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Delete NAV assignment. Admin only. Item 37."""
    try:
        success = db.delete_assignment(assignment_id)
        if success:
            logger.info(f"NAV assignment {assignment_id} deleted by user {user['user_id']}")
            return RedirectResponse(url="/coach/assignments?message=Assignment removed", status_code=303)
        else:
            return RedirectResponse(url="/coach/assignments?error=Assignment not found", status_code=303)
    except Exception as e:
        logger.error(f"Error deleting assignment: {e}")
        return RedirectResponse(url=f"/coach/assignments?error={str(e)}", status_code=303)

@app.get("/team/assigned-navs", response_class=HTMLResponse)
async def team_assigned_navs(request: Request, user: dict = Depends(require_login)):
    """View assigned NAVs for competitor. Item 37."""
    try:
        # Get user's active pairing
        pairing = db.get_active_pairing_for_member(user["user_id"])
        
        if not pairing:
            return templates.TemplateResponse("team/assigned_navs.html", {
                "request": request,
                "user": user,
                "pairing": None,
                "active_assignments": [],
                "completed_assignments": []
            })
        
        # Get active and completed assignments
        active_assignments = db.get_assignments_for_pairing(pairing["id"], completed=False)
        completed_assignments = db.get_assignments_for_pairing(pairing["id"], completed=True)
        
        return templates.TemplateResponse("team/assigned_navs.html", {
            "request": request,
            "user": user,
            "pairing": pairing,
            "active_assignments": active_assignments,
            "completed_assignments": completed_assignments
        })
    except Exception as e:
        logger.error(f"Error displaying assigned NAVs: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "user": user,
            "error": f"Error loading assigned NAVs: {str(e)}"
        })

@app.get("/assignments/{assignment_id}", response_class=HTMLResponse)
async def assignment_workflow(assignment_id: int, request: Request, user: dict = Depends(require_login)):
    """View single assignment workflow page. Item 37."""
    try:
        logger.info(f"User {user['user_id']} accessing assignment {assignment_id}")
        
        # Get assignment details
        assignment = db.get_assignment(assignment_id)
        
        if not assignment:
            logger.warning(f"Assignment {assignment_id} not found for user {user['user_id']}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "user": user,
                "error": "Assignment not found"
            })
        
        logger.info(f"Assignment found: pairing_id={assignment.get('pairing_id')}, nav_id={assignment.get('nav_id')}")
        
        # Verify pairing_id and nav_id exist
        if "pairing_id" not in assignment or "nav_id" not in assignment:
            logger.error(f"Assignment {assignment_id} missing pairing_id or nav_id. Keys: {list(assignment.keys())}")
            raise ValueError("Assignment is missing pairing_id or nav_id")
        
        # Verify user has access (in the pairing or is coach/admin)
        pairing = db.get_pairing(assignment["pairing_id"])
        if not pairing:
            logger.warning(f"Pairing {assignment['pairing_id']} not found for assignment {assignment_id}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "user": user,
                "error": "Pairing not found"
            })
        is_in_pairing = (
            user["user_id"] == pairing.get("pilot_id") or
            user["user_id"] == pairing.get("safety_observer_id")
        )
        
        if not is_in_pairing and not user.get("is_coach") and not user.get("is_admin"):
            logger.warning(f"User {user['user_id']} does not have access to assignment {assignment_id}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "user": user,
                "error": "You don't have access to this assignment"
            })
        
        # Check if pre-flight submitted
        prenav = db.get_open_prenav_submissions(is_coach=False)
        has_prenav = any(
            p.get("pairing_id") == assignment["pairing_id"] and
            p.get("nav_id") == assignment["nav_id"]
            for p in prenav
        )
        
        # Check if post-flight submitted (assignment completed)
        has_postnav = assignment.get("completed_at") is not None
        
        # Get result ID if completed
        result_id = None
        if has_postnav:
            # Find the flight result for this assignment
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM flight_results
                    WHERE pairing_id = ? AND nav_id = ?
                    ORDER BY scored_at DESC LIMIT 1
                """, (assignment["pairing_id"], assignment["nav_id"]))
                row = cursor.fetchone()
                if row:
                    result_id = row[0]
        
        logger.info(f"Successfully loaded assignment {assignment_id} for user {user['user_id']}")
        
        return templates.TemplateResponse("team/assignment_workflow.html", {
            "request": request,
            "user": user,
            "assignment": assignment,
            "pairing": pairing,
            "has_prenav": has_prenav,
            "has_postnav": has_postnav,
            "result_id": result_id
        })
    except Exception as e:
        logger.error(f"Error displaying assignment workflow for assignment {assignment_id}: {e}", exc_info=True)
        return templates.TemplateResponse("error.html", {
            "request": request,
            "user": user,
            "error": f"Error loading assignment: {str(e)}"
        })

# ===== ACTIVITY LOG ROUTES (Item 38) =====

@app.get("/coach/activity-log", response_class=HTMLResponse)
async def coach_activity_log(
    request: Request,
    user: dict = Depends(require_coach),
    user_id: Optional[str] = None,
    category: Optional[str] = None,
    activity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1
):
    """View activity log with filtering. Coach/Admin only. Item 38."""
    try:
        # Convert query params
        filters = {
            "user_id": int(user_id) if user_id else None,
            "category": category,
            "activity_type": activity_type,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Pagination
        limit = 50
        offset = (page - 1) * limit
        
        # Get filtered logs
        logs = db.get_activity_log(
            user_id=filters["user_id"],
            category=filters["category"],
            activity_type=filters["activity_type"],
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_entries = db.get_activity_count(
            user_id=filters["user_id"],
            category=filters["category"]
        )
        total_pages = (total_entries + limit - 1) // limit
        
        # Get all users for filter dropdown
        all_users = db.list_users()
        
        # Get unique categories and types from database
        categories = ["auth", "nav", "flight", "admin", "user", "pairing"]
        activity_types_list = [
            "login", "logout", "signup", "password_reset", "email_changed",
            "nav_created", "nav_edited", "nav_deleted",
            "airport_created", "airport_deleted",
            "gate_created", "gate_deleted",
            "checkpoint_created", "checkpoint_edited", "checkpoint_deleted",
            "secret_created", "secret_deleted",
            "prenav_submitted", "postnav_submitted",
            "user_created", "user_edited", "user_deleted", "user_approved", "user_denied",
            "pairing_created", "pairing_broken", "pairing_reactivated", "pairing_deleted",
            "config_updated", "backup_created"
        ]
        
        return templates.TemplateResponse("coach/activity_log.html", {
            "request": request,
            "user": user,
            "logs": logs,
            "filters": filters,
            "page": page,
            "total_pages": total_pages,
            "total_entries": total_entries,
            "users": all_users,
            "categories": categories,
            "activity_types": activity_types_list,
            "is_admin": user["is_admin"]
        })
    except Exception as e:
        logger.error(f"Error displaying activity log: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "user": user,
            "error": f"Error loading activity log: {str(e)}"
        })

@app.get("/coach/activity-log/{log_id}")
async def coach_activity_log_detail(
    log_id: int,
    request: Request,
    user: dict = Depends(require_coach)
):
    """Get details for a single activity log entry. Returns JSON. Item 38."""
    try:
        logs = db.get_activity_log(limit=1, offset=0)
        # Find the specific log by ID
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activity_log WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            if row:
                log = dict(row)
                return {"success": True, "log": log}
            else:
                return {"success": False, "message": "Log entry not found"}
    except Exception as e:
        logger.error(f"Error fetching activity log detail: {e}")
        return {"success": False, "message": str(e)}

@app.get("/coach/activity-log/export")
async def coach_activity_log_export(
    request: Request,
    user: dict = Depends(require_coach),
    user_id: Optional[str] = None,
    category: Optional[str] = None,
    activity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Export activity log to CSV. Coach/Admin only. Item 38."""
    import csv
    from io import StringIO
    from starlette.responses import StreamingResponse
    
    try:
        # Get all matching logs (no limit)
        logs = db.get_activity_log(
            user_id=int(user_id) if user_id else None,
            category=category,
            activity_type=activity_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Max export limit
            offset=0
        )
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Timestamp",
            "User ID",
            "User Name",
            "User Email",
            "Category",
            "Activity Type",
            "Details",
            "Related Entity Type",
            "Related Entity ID",
            "IP Address"
        ])
        
        # Write data rows
        for log in logs:
            writer.writerow([
                log.get("timestamp", ""),
                log.get("user_id", ""),
                log.get("user_name", ""),
                log.get("user_email", ""),
                log.get("activity_category", ""),
                log.get("activity_type", ""),
                log.get("activity_details", ""),
                log.get("related_entity_type", ""),
                log.get("related_entity_id", ""),
                log.get("ip_address", "")
            ])
        
        # Create response
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=activity_log.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting activity log: {e}")
        return {"success": False, "message": str(e)}

# ===== STARTUP/SHUTDOWN =====

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
