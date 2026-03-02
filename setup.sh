#!/bin/bash
# Parivaar Health - Quick Setup Script
# Run this from the parivaar_health/ directory

echo "=== Parivaar Health Setup ==="

# Install dependencies
echo "[1/4] Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "[2/4] Creating database..."
python manage.py makemigrations accounts medicines calendar_app vault
python manage.py migrate

# Create superuser
echo "[3/4] Creating admin user..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

# Collect static files
echo "[4/4] Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Start the server with: python manage.py runserver"
echo ""
echo "Then visit:"
echo "  App:   http://127.0.0.1:8000/"
echo "  Admin: http://127.0.0.1:8000/admin/"
echo ""
echo "Admin credentials: admin / admin123"
echo ""
echo "Register a new user at: http://127.0.0.1:8000/accounts/register/"
