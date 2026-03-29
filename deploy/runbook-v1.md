# Belivia V1 Deploy Runbook

## Zweck
Dieses Runbook beschreibt den kleinen manuellen Standard-Deploy-Ablauf für Belivia 2.0 in der aktuellen V1-Struktur.

## Grundprinzip
- GitHub ist die führende Projektquelle
- das lokale Repo ist die Arbeitsquelle
- der Server ist die Laufzeitumgebung
- Deploys erfolgen kontrolliert und manuell
- keine direkte Arbeit im laufenden Serverstand als Primärquelle

## Typischer Ablauf

### 1. Lokal arbeiten
Im lokalen Repo:
- Änderungen umsetzen
- lokal prüfen
- committen
- nach GitHub pushen

### 2. Dateien ins Server-Staging kopieren
Relevante Dateien per `scp` nach:
- `~/belivia-deploy-staging`

Typische V1-Dateien:
- `backend/app/main.py`
- `admin/index.html`
- `frontend/index.html`

Optional zusätzlich:
- `deploy/systemd/belivia-api.service`
- `deploy/nginx/belivia-preview.conf`
- `deploy/nginx/belivia-admin.conf`

### 3. Live-Übernahme auf dem Server
Auf dem Server per `sudo install` an die Zielorte übernehmen.

Aktuelle Zielorte:
- `/srv/belivia/backend/app/main.py`
- `/srv/belivia/admin-frontend/index.html`
- `/srv/belivia/frontend-preview/index.html`

Optional:
- `/etc/systemd/system/belivia-api.service`
- `/etc/nginx/sites-available/belivia-preview`
- `/etc/nginx/sites-available/belivia-admin`

### 4. Dienste neu laden
Je nach Änderung:
- `sudo systemctl restart belivia-api`
- `sudo systemctl reload nginx`
- optional `sudo systemctl daemon-reload` bei systemd-Änderungen
- optional `sudo nginx -t` vor Nginx-Reload bei Nginx-Änderungen

### 5. Verifikation
Nach jedem Deploy:
- Dienststatus prüfen
- lokalen API-Healthcheck prüfen
- Admin-API kurz prüfen
- Preview-Auslieferung prüfen
- externe Erreichbarkeit nur bei Bedarf zusätzlich gegenprüfen

## Backup

### Manuelles Backup ausführen
Script liegt im Repo unter `deploy/scripts/backup-v1.sh`.
Auf dem Server unter `/srv/belivia/ops/scripts/backup-v1.sh` ablegen (einmalig, nach erstem Deploy des Scripts).

```bash
bash /srv/belivia/ops/scripts/backup-v1.sh
```

Backup-Ziel: `/srv/belivia/ops/backups/belivia-YYYYMMDD-HHMMSS.sqlite`
Aufbewahrung: letzte 7 Kopien, ältere werden automatisch gelöscht.

### Backup prüfen
```bash
ls -lh /srv/belivia/ops/backups/
```

## Restore

**Voraussetzung:** Dienst muss gestoppt sein, bevor die Datenbankdatei ersetzt wird.

```bash
# 1. Dienst stoppen
sudo systemctl stop belivia-api

# 2. Aktuelle DB sichern (Vorsicht-Kopie)
cp /srv/belivia/data/belivia.sqlite /srv/belivia/data/belivia.sqlite.before-restore

# 3. Backup einspielen (gewünschte Datei einsetzen)
sudo install -o beliviaapp -g beliviaapp -m 644 \
  /srv/belivia/ops/backups/belivia-YYYYMMDD-HHMMSS.sqlite \
  /srv/belivia/data/belivia.sqlite

# 4. Dienst wieder starten
sudo systemctl start belivia-api

# 5. Verifikation
systemctl is-active belivia-api
curl -sS http://127.0.0.1:8000/api/health
```

## Standard-Post-Deploy-Verifikation
```bash
echo "=== SERVICES ==="
systemctl is-active belivia-api
systemctl is-active nginx
echo ---
echo "=== LOCAL HEALTH ==="
curl -sS http://127.0.0.1:8000/api/health
echo
echo ---
echo "=== ADMIN API ==="
curl -sS -H "Host: admin.belivia-alltagsbegleitung.de" http://127.0.0.1:8082/api/admin/requests?limit=1
echo
echo ---
echo "=== PREVIEW HTML ==="
curl -sS -H "Host: new.belivia-alltagsbegleitung.de" http://127.0.0.1:8081/ | head -n 5
echo
