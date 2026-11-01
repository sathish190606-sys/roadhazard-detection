import smtplib
import datetime
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import Hazard, AlertLog

logger = logging.getLogger(__name__)

# In-memory rate limiting cache: key -> datetime of last alert
_alert_rate_cache = {}

def is_rate_limited(hazard: Hazard) -> bool:
    """Checks whether an alert for a similar hazard was dispatched within the rate limit window."""
    now = datetime.datetime.utcnow()
    # Rate limit key based on hazard class and coarse lat/lon
    key = f"{hazard.hazard_class}:{round(hazard.latitude, 3)}:{round(hazard.longitude, 3)}"
    
    last_sent = _alert_rate_cache.get(key)
    if last_sent:
        elapsed = (now - last_sent).total_seconds() / 60.0
        if elapsed < settings.ALERT_RATE_LIMIT_MINUTES:
            return True
    
    _alert_rate_cache[key] = now
    return False

def send_email_alert(hazard: Hazard, db: Optional[Session] = None) -> bool:
    if not settings.SMTP_ENABLED:
        logger.debug("SMTP alerts disabled in configuration.")
        return False

    subject = f"[ROAD HAZARD ALERT] High Severity {hazard.hazard_class.upper()} Detected (Score: {hazard.severity_score})"
    body = f"""URGENT ROAD HAZARD ALERT
------------------------------------------------
Hazard Type: {hazard.hazard_class.upper()}
Severity Score: {hazard.severity_score} / 100
Confidence: {round(hazard.confidence * 100, 1)}%
Location: Lat {hazard.latitude}, Lon {hazard.longitude}
Reported by: Robot {hazard.robot_id}
Timestamp: {hazard.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Clustered Reports: {hazard.cluster_count}

Please review immediately on the patrol dashboard.
"""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.ALERT_RECIPIENT_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Email alert dispatched successfully to {settings.ALERT_RECIPIENT_EMAIL}")

        if db:
            log = AlertLog(
                hazard_id=hazard.id,
                channel="email",
                recipient=settings.ALERT_RECIPIENT_EMAIL,
                status="sent",
                message=subject
            )
            db.add(log)
            db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        if db:
            log = AlertLog(
                hazard_id=hazard.id,
                channel="email",
                recipient=settings.ALERT_RECIPIENT_EMAIL,
                status="failed",
                message=str(e)
            )
            db.add(log)
            db.commit()
        return False

def send_sms_alert(hazard: Hazard, db: Optional[Session] = None) -> bool:
    if not settings.TWILIO_ENABLED:
        logger.debug("Twilio SMS alerts disabled in configuration.")
        return False

    message_body = (
        f"HAZARD ALERT: {hazard.hazard_class.upper()} (Score: {hazard.severity_score}) "
        f"detected at Lat {hazard.latitude:.4f}, Lon {hazard.longitude:.4f} by {hazard.robot_id}."
    )
    try:
        # Dynamic import so twilio is an optional dependency
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message_body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=settings.ALERT_RECIPIENT_SMS
        )
        logger.info(f"SMS alert dispatched successfully to {settings.ALERT_RECIPIENT_SMS}")

        if db:
            log = AlertLog(
                hazard_id=hazard.id,
                channel="sms",
                recipient=settings.ALERT_RECIPIENT_SMS,
                status="sent",
                message=message_body
            )
            db.add(log)
            db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS alert via Twilio: {e}")
        if db:
            log = AlertLog(
                hazard_id=hazard.id,
                channel="sms",
                recipient=settings.ALERT_RECIPIENT_SMS,
                status="failed",
                message=str(e)
            )
            db.add(log)
            db.commit()
        return False

def trigger_alerts_if_eligible(hazard: Hazard, db: Optional[Session] = None):
    """Evaluates severity threshold and dispatches rate-limited notifications."""
    if hazard.severity_score < settings.ALERT_SEVERITY_THRESHOLD:
        return

    if is_rate_limited(hazard):
        logger.info(f"Alert for hazard {hazard.id} suppressed due to rate limiting window.")
        return

    logger.warning(
        f"High severity hazard {hazard.id} ({hazard.hazard_class}) triggered! "
        f"Score: {hazard.severity_score} >= {settings.ALERT_SEVERITY_THRESHOLD}"
    )
    send_email_alert(hazard, db)
    send_sms_alert(hazard, db)
