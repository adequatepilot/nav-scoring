#!/bin/bash

# NAV Scoring Deployment Verification Script
# Checks all requirements for successful UI/UX deployment

set -e

echo "=========================================="
echo "NAV Scoring UI/UX Deployment Verification"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
check_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_failure() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# 1. Check Docker Image
echo "1. Checking Docker Image..."
if docker images | grep -q "nav_scoring.*latest"; then
    check_success "Docker image exists: nav_scoring:latest"
else
    check_failure "Docker image not found: nav_scoring:latest"
fi

# 2. Check Container Status
echo ""
echo "2. Checking Container Status..."
if docker ps | grep -q "nav_scoring"; then
    check_success "Container is running"
    CONTAINER_RUNNING=true
else
    check_warning "Container is not running (should start with docker-compose up -d)"
    CONTAINER_RUNNING=false
fi

# 3. Check Static Files
echo ""
echo "3. Checking Static Files..."

if [ -f "static/styles.css" ]; then
    check_success "styles.css exists"
    SIZE=$(wc -c < static/styles.css)
    if [ "$SIZE" -gt 4000 ]; then
        check_success "styles.css has sufficient size ($SIZE bytes)"
    else
        check_failure "styles.css is too small ($SIZE bytes)"
    fi
else
    check_failure "static/styles.css not found"
fi

if [ -d "static/images" ]; then
    check_success "static/images directory exists"
    if [ -f "static/images/README.md" ]; then
        check_success "static/images/README.md exists"
    else
        check_failure "static/images/README.md not found"
    fi
else
    check_failure "static/images directory not found"
fi

# 4. Check Template Files
echo ""
echo "4. Checking Template Files..."

TEMPLATES=(
    "templates/base.html"
    "templates/login.html"
    "templates/coach/navs.html"
    "templates/coach/dashboard.html"
    "templates/team/dashboard.html"
)

for template in "${TEMPLATES[@]}"; do
    if [ -f "$template" ]; then
        check_success "$template exists"
    else
        check_failure "$template not found"
    fi
done

# 5. Check Hamburger Menu Implementation
echo ""
echo "5. Checking Hamburger Menu Implementation..."

if grep -q "hamburger" templates/base.html; then
    check_success "Hamburger menu code found in base.html"
else
    check_failure "Hamburger menu code not found in base.html"
fi

if grep -q "nav-sidebar" templates/base.html; then
    check_success "Sidebar overlay code found in base.html"
else
    check_failure "Sidebar overlay code not found in base.html"
fi

if grep -q "768px" templates/base.html; then
    check_success "Mobile breakpoint (768px) found in base.html"
else
    check_failure "Mobile breakpoint not found in base.html"
fi

# 6. Check SIU Branding Colors
echo ""
echo "6. Checking SIU Branding Colors..."

if grep -q "#8B0015" templates/base.html; then
    check_success "SIU maroon color (#8B0015) found in base.html"
else
    check_failure "SIU maroon color not found in base.html"
fi

if grep -q "#8B0015" static/styles.css; then
    check_success "SIU maroon color (#8B0015) found in styles.css"
else
    check_failure "SIU maroon color not found in styles.css"
fi

if grep -q "siu-logo" templates/login.html; then
    check_success "SIU logo placeholder found in login.html"
else
    check_failure "SIU logo placeholder not found in login.html"
fi

# 7. Check NAV Management Page Simplification
echo ""
echo "7. Checking NAV Management Page Simplification..."

# Count nav-card occurrences in navs.html
CARD_COUNT=$(grep -o "nav-card" templates/coach/navs.html | wc -l)

if [ "$CARD_COUNT" -eq 2 ]; then
    check_success "NAV page has exactly 2 cards (found: $CARD_COUNT)"
else
    check_failure "NAV page should have 2 cards but has: $CARD_COUNT"
fi

if ! grep -q "Start Gates" templates/coach/navs.html; then
    check_success "Start Gates card removed from main NAV page"
else
    check_warning "Start Gates card still present in main NAV page"
fi

if ! grep -q "Checkpoints" templates/coach/navs.html; then
    check_success "Checkpoints card removed from main NAV page"
else
    check_warning "Checkpoints card still present in main NAV page"
fi

if ! grep -q "Secrets" templates/coach/navs.html; then
    check_success "Secrets card removed from main NAV page"
else
    check_warning "Secrets card still present in main NAV page"
fi

# 8. Check Container File Verification (if running)
echo ""
echo "8. Checking Container Files..."

if [ "$CONTAINER_RUNNING" = true ]; then
    if docker exec nav_scoring test -f /app/static/styles.css; then
        check_success "styles.css found in container"
    else
        check_failure "styles.css not found in container"
    fi
    
    if docker exec nav_scoring test -d /app/static/images; then
        check_success "images directory found in container"
    else
        check_failure "images directory not found in container"
    fi
else
    check_warning "Cannot verify container files - container not running"
fi

# 9. Check Python Syntax
echo ""
echo "9. Checking Python Syntax..."

if python3 -m py_compile app/*.py 2>/dev/null; then
    check_success "All Python files compile successfully"
else
    check_failure "Python syntax errors found in app files"
fi

# 10. Check Navbar Updates
echo ""
echo "10. Checking Navbar Updates..."

NAVBAR_FILES=(
    "templates/coach/dashboard.html"
    "templates/coach/results.html"
    "templates/coach/members.html"
    "templates/coach/pairings.html"
    "templates/coach/config.html"
    "templates/coach/navs.html"
    "templates/team/dashboard.html"
    "templates/team/prenav.html"
    "templates/team/flight.html"
)

for file in "${NAVBAR_FILES[@]}"; do
    if [ -f "$file" ]; then
        if grep -q "navbar-brand" "$file"; then
            check_success "$file has navbar-brand structure"
        else
            check_warning "$file missing navbar-brand structure"
        fi
    fi
done

# Summary
echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC}  $PASSED"
echo -e "${RED}Failed:${NC}  $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

if [ "$FAILED" -eq 0 ]; then
    if [ "$WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed!${NC}"
        echo ""
        echo "Deployment is ready. Run:"
        echo "  docker-compose up -d"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}⚠ Checks passed but with warnings${NC}"
        echo ""
        echo "Review warnings above. To deploy:"
        echo "  docker-compose up -d"
        echo ""
        exit 0
    fi
else
    echo -e "${RED}✗ Deployment verification failed${NC}"
    echo ""
    echo "Issues found:"
    echo "1. Review failed checks above"
    echo "2. Ensure all files are properly created"
    echo "3. Run: docker build -t nav_scoring:latest ."
    echo "4. Re-run this script"
    echo ""
    exit 1
fi
