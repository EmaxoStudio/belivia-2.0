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

Das Restore-Script liegt im Repo unter `deploy/scripts/restore-v1.sh`.
Auf dem Server ablegen unter `/srv/belivia/ops/scripts/restore-v1.sh`.

### Verfügbare Backups anzeigen

```bash
ls -lht /srv/belivia/ops/backups/
```

### Backup-Integrität manuell prüfen (optional, vor Restore)

```bash
sqlite3 /srv/belivia/ops/backups/belivia-YYYYMMDD-HHMMSS.sqlite "PRAGMA integrity_check;"
# Erwartet: ok
```

### Restore per Script ausführen

```bash
bash /srv/belivia/ops/scripts/restore-v1.sh \
  /srv/belivia/ops/backups/belivia-YYYYMMDD-HHMMSS.sqlite
```

Das Script:
1. Prüft Backup-Integrität (SQLite PRAGMA integrity_check)
2. Zeigt Tabellenübersicht des Backups
3. Fragt zur Bestätigung (kein automatischer Restore)
4. Stoppt belivia-api
5. Erstellt Sicherheitskopie der aktuellen DB als `.before-restore`
6. Installiert Backup mit korrekten Berechtigungen (beliviaapp:beliviaapp 644)
7. Startet belivia-api
8. Führt Post-Restore-Verifikation durch

### Post-Restore-Verifikation

```bash
# Dienststatus
systemctl is-active belivia-api
systemctl is-active nginx

# Health-Endpunkt
curl -sS http://127.0.0.1:8000/api/health

# DB-Tabellen der wiederhergestellten Datenbank
sqlite3 /srv/belivia/data/belivia.sqlite ".tables"
```

### Nach bestätigtem Restore: Sicherheitskopie aufräumen

```bash
rm /srv/belivia/data/belivia.sqlite.before-restore
```

### Rollback (Restore rückgängig machen)

Falls etwas nicht stimmt, vor dem Aufräumen der Sicherheitskopie:

```bash
sudo systemctl stop belivia-api
sudo install -o beliviaapp -g beliviaapp -m 644 \
  /srv/belivia/data/belivia.sqlite.before-restore \
  /srv/belivia/data/belivia.sqlite
sudo systemctl start belivia-api
systemctl is-active belivia-api
curl -sS http://127.0.0.1:8000/api/health
```

### Wichtige Hinweise

- **Dienst muss gestoppt sein** vor dem Ersetzen der Datenbankdatei — SQLite ist nicht concurrent-write-safe
- **Backup-Integrität immer prüfen** bevor ein Backup eingespielt wird
- **Sicherheitskopie erst löschen** wenn Restore vollständig bestätigt ist
- **`.before-restore`-Dateien nicht anhäufen** — nur eine gleichzeitig, danach aufräumen

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
