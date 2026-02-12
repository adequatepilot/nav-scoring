#!/bin/bash
# NAV Scoring - Validation Script
# Checks that all deliverables are in place

echo "🔍 NAV Scoring - Validation Check"
echo "=================================="
echo ""

errors=0

# Check app.py
echo "1. Checking app.py..."
if [ -f "app/app.py" ]; then
    lines=$(wc -l < app/app.py)
    echo "   ✅ app.py exists ($lines lines)"
    
    # Check for key routes
    if grep -q "GET /prenav" app/app.py && \
       grep -q "POST /prenav" app/app.py && \
       grep -q "POST /flight" app/app.py && \
       grep -q "GET /coach" app/app.py; then
        echo "   ✅ All major routes present"
    else
        echo "   ❌ Missing some routes"
        ((errors++))
    fi
    
    # Check syntax
    if python3 -m py_compile app/app.py 2>/dev/null; then
        echo "   ✅ Python syntax valid"
    else
        echo "   ❌ Python syntax errors"
        ((errors++))
    fi
else
    echo "   ❌ app/app.py not found"
    ((errors++))
fi
echo ""

# Check templates
echo "2. Checking templates..."
templates=(
    "templates/base.html"
    "templates/login.html"
    "templates/team/prenav.html"
    "templates/team/prenav_confirmation.html"
    "templates/team/flight.html"
    "templates/team/results.html"
    "templates/team/results_list.html"
    "templates/coach/dashboard.html"
    "templates/coach/results.html"
    "templates/coach/members.html"
    "templates/coach/pairings.html"
    "templates/coach/config.html"
)

template_count=0
for template in "${templates[@]}"; do
    if [ -f "$template" ]; then
        ((template_count++))
    else
        echo "   ❌ Missing: $template"
        ((errors++))
    fi
done

echo "   ✅ $template_count/${#templates[@]} templates found"
echo ""

# Check foundation files
echo "3. Checking foundation files..."
foundation=(
    "app/database.py"
    "app/models.py"
    "app/auth.py"
    "app/scoring_engine.py"
    "app/email.py"
)

for file in "${foundation[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ Missing: $file"
        ((errors++))
    fi
done
echo ""

# Check config
echo "4. Checking configuration..."
if [ -f "config/config.yaml" ]; then
    echo "   ✅ config/config.yaml exists"
    
    # Check YAML syntax
    if python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))" 2>/dev/null; then
        echo "   ✅ YAML syntax valid"
    else
        echo "   ❌ YAML syntax errors"
        ((errors++))
    fi
else
    echo "   ❌ config/config.yaml not found"
    ((errors++))
fi
echo ""

# Check requirements
echo "5. Checking requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo "   ✅ requirements.txt exists"
    
    # Check for key packages
    if grep -q "fastapi" requirements.txt && \
       grep -q "gpxpy" requirements.txt && \
       grep -q "matplotlib" requirements.txt && \
       grep -q "reportlab" requirements.txt; then
        echo "   ✅ All key dependencies listed"
    else
        echo "   ⚠️  Some dependencies may be missing"
    fi
else
    echo "   ❌ requirements.txt not found"
    ((errors++))
fi
echo ""

# Check database schema
echo "6. Checking database schema..."
if [ -f "migrations/001_initial_schema.sql" ]; then
    echo "   ✅ Database migration exists"
else
    echo "   ❌ migrations/001_initial_schema.sql not found"
    ((errors++))
fi
echo ""

# Check Docker files
echo "7. Checking Docker configuration..."
if [ -f "Dockerfile" ]; then
    echo "   ✅ Dockerfile exists"
else
    echo "   ❌ Dockerfile not found"
    ((errors++))
fi

if [ -f "docker-compose.yml" ]; then
    echo "   ✅ docker-compose.yml exists"
else
    echo "   ❌ docker-compose.yml not found"
    ((errors++))
fi
echo ""

# Summary
echo "=================================="
echo "📊 Validation Summary"
echo "=================================="

if [ $errors -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED!"
    echo ""
    echo "🚀 Ready for Docker deployment!"
    echo ""
    echo "Next steps:"
    echo "  1. docker build -t nav-scoring:latest ."
    echo "  2. Edit config/config.yaml with your email settings"
    echo "  3. docker-compose up -d"
    echo "  4. Initialize coach account"
    echo "  5. Access http://localhost:8000"
    exit 0
else
    echo "❌ VALIDATION FAILED"
    echo ""
    echo "Found $errors error(s). Please fix before deployment."
    exit 1
fi
