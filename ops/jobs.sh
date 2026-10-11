#!/bin/sh
# Jobs-Container: stündlich der Löschdienst, einmal täglich (ab 3 Uhr) das Aufräumen.
# Fristen hängen nicht an diesem Skript: Sie werden bei jedem Zugriff aus Zeitstempeln berechnet.
last_day=""
while true; do
    python manage.py loeschdienst || echo "Löschdienst fehlgeschlagen"
    today="$(date +%F)"
    if [ "$today" != "$last_day" ] && [ "$(date +%H)" -ge 3 ]; then
        python manage.py aufraeumen && last_day="$today" || echo "Aufräumen fehlgeschlagen"
    fi
    sleep 3600
done
