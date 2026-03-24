import os
import sqlite3
import smtplib
import ssl
import logging
from email.message import EmailMessage
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = "/srv/belivia/data/belivia.sqlite"

logger = logging.getLogger("belivia")

app = FastAPI(title="Belivia API")

def db_conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

class ContactIn(BaseModel):
    name: str
    email: str
    phone: str | None = None
    message: str
    source: str | None = None
    event_date: str | None = None

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/contact")
def create_contact(payload: ContactIn):
    name = payload.name.strip()
    email = payload.email.strip()
    message = payload.message.strip()
    phone = (payload.phone or "").strip() or None
    source = (payload.source or "").strip() or None
    event_date = (payload.event_date or "").strip() or None

    if not name:
        raise HTTPException(status_code=400, detail="name_required")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="email_invalid")
    if not message:
        raise HTTPException(status_code=400, detail="message_required")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO contact_requests
        (name, email, phone, message, source, event_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, email, phone, message, source, event_date),
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()

    add_request_event(new_id, "request_created", "Contact request created")

    mail_status, mail_error = send_internal_contact_mail(
        contact_id=new_id,
        name=name,
        email=email,
        phone=phone,
        message=message,
        source=source,
        event_date=event_date,
    )

    update_mail_state(new_id, mail_status, mail_error)

    if mail_status == "sent":
        add_request_event(new_id, "mail_sent", "Internal notification mail sent")
    elif mail_status == "failed":
        add_request_event(new_id, "mail_failed", mail_error)
    elif mail_status == "skipped_not_configured":
        add_request_event(new_id, "mail_skipped", "Mail config incomplete")

    return {"status": "ok", "id": new_id, "mail_status": mail_status}

@app.get("/api/admin/requests")
def admin_requests(limit: int = 20, status: str | None = None):
    limit = max(1, min(limit, 200))

    con = db_conn()
    cur = con.cursor()

    if status:
        cur.execute(
            """
            SELECT id, created_at, name, email, phone, message, source, status, internal_note, event_date, mail_status, mail_last_attempt_at, mail_last_error
            FROM contact_requests
            WHERE status = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (status, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, created_at, name, email, phone, message, source, status, internal_note, event_date, mail_status, mail_last_attempt_at, mail_last_error
            FROM contact_requests
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    items = [dict(row) for row in cur.fetchall()]
    con.close()

    return {"count": len(items), "items": items}

@app.post("/api/admin/requests/{request_id}/status")
def admin_update_request_status(request_id: int, status: str):
    allowed = {"new", "in_progress", "done", "archived"}

    if status not in allowed:
        raise HTTPException(status_code=400, detail="status_invalid")

    con = db_conn()
    cur = con.cursor()
    cur.execute(
        "UPDATE contact_requests SET status = ? WHERE id = ?",
        (status, request_id),
    )
    con.commit()

    if cur.rowcount == 0:
        con.close()
        raise HTTPException(status_code=404, detail="request_not_found")

    con.close()
    add_request_event(request_id, "status_changed", f"Status changed to: {status}")
    return {"status": "ok", "id": request_id, "new_status": status}

class NoteIn(BaseModel):
    internal_note: str | None = None

@app.post("/api/admin/requests/{request_id}/note")
def admin_update_request_note(request_id: int, payload: NoteIn):
    note = (payload.internal_note or "").strip() or None

    con = db_conn()
    cur = con.cursor()
    cur.execute(
        "UPDATE contact_requests SET internal_note = ? WHERE id = ?",
        (note, request_id),
    )
    con.commit()

    if cur.rowcount == 0:
        con.close()
        raise HTTPException(status_code=404, detail="request_not_found")

    con.close()
    add_request_event(request_id, "note_updated", note or "")
    return {"status": "ok", "id": request_id, "internal_note": note}

@app.get("/api/admin/day-overview")
def admin_day_overview(day: str | None = None):
    con = db_conn()
    cur = con.cursor()

    if day:
        selected_day = day
    else:
        selected_day = cur.execute(
            "SELECT date('now','localtime')"
        ).fetchone()[0]

    total_created = cur.execute(
        "SELECT COUNT(*) FROM contact_requests WHERE date(created_at) = ?",
        (selected_day,),
    ).fetchone()[0]

    rows = cur.execute(
        """
        SELECT status, COUNT(*) as cnt
        FROM contact_requests
        WHERE date(created_at) = ?
        GROUP BY status
        """,
        (selected_day,),
    ).fetchall()

    created_by_status = {row["status"]: row["cnt"] for row in rows}

    event_rows = cur.execute(
        """
        SELECT id, name, email, phone, status, event_date
        FROM contact_requests
        WHERE event_date = ?
        ORDER BY id DESC
        """,
        (selected_day,),
    ).fetchall()

    events_on_day = [dict(row) for row in event_rows]

    con.close()

    return {
        "day": selected_day,
        "created_total": total_created,
        "created_by_status": created_by_status,
        "events_total": len(events_on_day),
        "events_on_day": events_on_day,
    }

def send_internal_contact_mail(contact_id: int, name: str, email: str, phone: str | None, message: str, source: str | None, event_date: str | None):
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_starttls = os.getenv("SMTP_STARTTLS", "true").strip().lower() == "true"
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "")
    mail_from = os.getenv("MAIL_FROM", "").strip()
    mail_to = os.getenv("MAIL_TO", "").strip()
    smtp_timeout = int(os.getenv("SMTP_TIMEOUT", "10"))

    if not all([smtp_host, smtp_user, smtp_pass, mail_from, mail_to]):
        logger.warning("internal_contact_mail_skipped_not_configured id=%s", contact_id)
        return ("skipped_not_configured", None)

    msg = EmailMessage()
    msg["Subject"] = f"[Belivia] Neue Anfrage #{contact_id}"
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg.set_content(
        "Neue Kontaktanfrage\n\n"
        f"ID: {contact_id}\n"
        f"Name: {name}\n"
        f"E-Mail: {email}\n"
        f"Telefon: {phone or ''}\n"
        f"Event-Datum: {event_date or ''}\n"
        f"Quelle: {source or ''}\n\n"
        "Nachricht:\n"
        f"{message}\n"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout) as smtp:
            smtp.ehlo()
            if smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        return ("sent", None)
    except Exception as e:
        logger.exception("internal_contact_mail_failed id=%s", contact_id)
        return ("failed", str(e))

def add_request_event(request_id: int, event_type: str, event_data: str | None = None):
    con = db_conn()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO request_events (request_id, event_type, event_data)
        VALUES (?, ?, ?)
        """,
        (request_id, event_type, event_data),
    )
    con.commit()
    con.close()

def update_mail_state(request_id: int, mail_status: str, mail_last_error: str | None = None):
    con = db_conn()
    cur = con.cursor()
    cur.execute(
        """
        UPDATE contact_requests
        SET mail_status = ?,
            mail_last_attempt_at = CURRENT_TIMESTAMP,
            mail_last_error = ?
        WHERE id = ?
        """,
        (mail_status, mail_last_error, request_id),
    )
    con.commit()
    con.close()

@app.get("/api/admin/requests/{request_id}/events")
def admin_request_events(request_id: int):
    con = db_conn()
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, request_id, created_at, event_type, event_data
        FROM request_events
        WHERE request_id = ?
        ORDER BY id ASC
        """,
        (request_id,),
    )
    items = [dict(row) for row in cur.fetchall()]
    con.close()

    return {"count": len(items), "items": items}
