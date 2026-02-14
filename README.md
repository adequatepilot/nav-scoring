# NAV Scoring System

A complete NIFA NAV scoring application for piloting competitions. Handles pre-flight planning, GPS-based post-flight analysis, and automatic score generation with PDF reports.

## Features

- 🎯 **Pre-Flight Planning** - Submit leg times and fuel estimates before flight
- 📍 **GPS Tracking** - Upload GPX files and automatic scoring calculations
- 📊 **Score Reports** - Auto-generated PDF reports with track plots
- 📧 **Email Notifications** - Automated prenav and results email delivery
- 👥 **Member Management** - Manage pilots, observers, and pairings with bulk CSV import
- 🎓 **Coach Dashboard** - View all results, filter by team/NAV/date
- 🔐 **Secure Authentication** - Session-based login with role-based access

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Modern web browser

### 1 Minute Start

```bash
# Clone and navigate to the repo
cd nav_scoring

# Copy config template
cp config.yaml.template data/config.yaml

# Edit config with your email settings (optional for initial testing)
nano data/config.yaml

# Start the application
docker-compose up -d

# Initialize the coach account
docker exec nav-scoring python3 seed.py

# Open in browser
# http://localhost:8000
```

**Default Login:** coach / changeme123 (change immediately!)

For detailed setup instructions, see [QUICK_START.md](docs/QUICK_START.md).

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Step-by-step setup and first-run instructions
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment on Unraid and other platforms
- **[Mobile Testing Guide](docs/MOBILE_TESTING.md)** - Testing on mobile devices
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Common commands and API reference
- **[GitHub Setup](docs/GITHUB_SETUP.md)** - Contributing and releasing new versions
- **[Versioning Guide](docs/VERSIONING.md)** - Version management and release process

## Contributing

1. Create a GitHub token at https://github.com/settings/tokens/new
2. Configure credentials: `cp .github-credentials.template .github-credentials`
3. Run: `./scripts/setup-github.sh`

See [GITHUB_QUICKSTART.md](GITHUB_QUICKSTART.md) for quick setup or [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) for detailed instructions.

## Release Process

```bash
# Make your changes and commit
git commit -m "feat: your feature description"

# Create a release (patch, minor, or major)
./scripts/release.sh patch   # 1.0.0 → 1.0.1
./scripts/release.sh minor   # 1.0.0 → 1.1.0
./scripts/release.sh major   # 1.0.0 → 2.0.0
```

## Technology Stack

- **Backend:** Python 3 with Flask
- **Frontend:** HTML/CSS/JavaScript
- **Database:** SQLite
- **GPS Processing:** gpxpy
- **PDF Generation:** reportlab
- **Charts:** matplotlib
- **Email:** SMTP (Zoho Mail compatible)
- **Containerization:** Docker & Docker Compose

## Project Structure

```
nav-scoring/
├── app/                      # Application code
│   ├── __init__.py
│   ├── database.py          # SQLite database layer
│   ├── auth.py              # Authentication & authorization
│   ├── scoring.py           # NAV scoring engine
│   ├── email.py             # Email notifications
│   ├── gps.py               # GPX parsing & analysis
│   ├── pdf.py               # PDF report generation
│   └── routes.py            # Flask routes
├── templates/               # HTML templates
├── static/                  # CSS, images, logo
├── config/                  # Configuration files
├── migrations/              # Database schemas
├── scripts/                 # Release & setup scripts
├── docs/                    # Documentation
├── config.yaml.template     # Configuration template
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Multi-container setup
├── seed.py                 # Database initialization
├── VERSION                 # Version string
└── CHANGELOG.md            # Release history
```

## Environment Variables

Key configuration in `data/config.yaml`:

```yaml
app:
  debug: false
  port: 8000
  
email:
  sender_email: "nav-scoring@example.com"
  sender_password: "your-app-password"
  recipients_coach: "coach@example.com"
  
database:
  path: "/app/data/navs.db"
```

## Common Issues

**"Database locked" error**
```bash
docker-compose restart
```

**Email not sending**
- Verify SMTP credentials in data/config.yaml
- Check container logs: `docker logs nav-scoring`
- Use Zoho app-specific password (not main password)

**GPX upload fails**
- Ensure file is valid .gpx (not .kml or .fit)
- File must contain track points
- Re-export from GPS device if corrupted

## License

Proprietary - Southern Illinois University Aviation

## Support

For issues and questions:
1. Check relevant documentation in `docs/`
2. Review application logs: `docker logs nav-scoring`
3. Verify configuration in `data/config.yaml`

---

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2026-02-12
