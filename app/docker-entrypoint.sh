#!/bin/sh
# Start des Backends: Migrationen, statische Dateien des Admin-Bereichs, Ortsliste beim ersten Start.
set -e
if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --no-input
    python manage.py collectstatic --no-input >/dev/null
    if [ -f /daten/places/gemeinden.csv ] && [ "$(python manage.py shell -c 'from places.models import Place; print(Place.objects.count())' | tail -1)" = "0" ]; then
        python manage.py orte_importieren /daten/places/gemeinden.csv
    fi
fi
exec "$@"
