#!/usr/bin/env bash
set -euo pipefail

echo ">> applying database migrations"
python manage.py migrate --noinput

if [ "${DJANGO_AUTO_SEED:-1}" = "1" ]; then
    HAS_USERS=$(python manage.py shell -c \
        "from apps.accounts.models import User; print(User.objects.exists())" \
        2>/dev/null | tail -1 | tr -d '[:space:]')
    if [ "$HAS_USERS" = "False" ]; then
        echo ">> empty database — seeding demo users, listings, and bookings"
        python manage.py seed_demo || echo ">> seed step failed, continuing without demo data"
    else
        echo ">> database already populated — skipping demo seed"
    fi
fi

echo ">> starting Django development server on 0.0.0.0:8000"
exec python manage.py runserver 0.0.0.0:8000
