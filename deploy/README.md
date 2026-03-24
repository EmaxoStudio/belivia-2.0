# Deploy

Dieser Ordner enthält die kleine V1-Deploy-/Ops-Struktur für Belivia 2.0.

## Ziel
Belivia wird ab jetzt repo-first geführt:

- GitHub ist die führende Projektquelle
- das lokale Repo auf dem Laptop ist die Arbeitsquelle
- der Server ist die Laufzeitumgebung

## Inhalt dieses Ordners
- `systemd/` systemd-Units für Belivia-Dienste
- `nginx/` Nginx-VHost-Konfigurationen
- `cloudflared/` Platz für deploybare Tunnel-/Edge-bezogene Vorlagen ohne Secrets
- `scripts/` optionale kleine Hilfsskripte für manuelle Deploy-/Ops-Schritte

## V1-Deploy-Prinzip
Kein CI/CD-Overkill.

Deploys erfolgen in V1 kontrolliert und manuell:
1. lokal ändern
2. lokal prüfen
3. commit + push
4. relevante Dateien per `scp` ins Server-Staging kopieren
5. serverseitig per `install` an die Zielorte übernehmen
6. Dienste reloaden/restarten
7. Verifikation ausführen

## Server-only / nicht im Repo
Diese Dinge bleiben bewusst außerhalb des Repos:
- `/srv/belivia/data`
- `/srv/belivia/ops`
- `backend/venv`
- `/etc/belivia/mail.env`
- `/etc/cloudflared/config.yml`
- Secrets / Credentials / DB-Inhalte / Logs

## Hinweis
Dieses Verzeichnis beschreibt die kleine V1-Ordnung.
Es ersetzt keine spätere ausgereifte CI/CD- oder Go-Live-Strategie.
