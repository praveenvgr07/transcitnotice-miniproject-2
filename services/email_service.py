"""Email service – supports SMTP and SendGrid."""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(
    cfg,
    to_address: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> tuple[bool, str]:
    """
    Send an email using the configured provider.
    Returns (success: bool, provider_ref_or_error: str).
    """
    provider = getattr(cfg, "MAIL_PROVIDER", "smtp")
    if provider == "sendgrid":
        return _send_sendgrid(cfg, to_address, subject, html_body, text_body)
    return _send_smtp(cfg, to_address, subject, html_body, text_body)


def _send_smtp(cfg, to_address, subject, html_body, text_body) -> tuple[bool, str]:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg.MAIL_FROM
    msg["To"]      = to_address

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
            server.sendmail(cfg.MAIL_FROM, [to_address], msg.as_string())
        logger.info("SMTP: email sent to %s | subject: %s", to_address, subject)
        return True, "smtp_ok"
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP: authentication failed")
        return False, "smtp_auth_failed"
    except smtplib.SMTPRecipientsRefused:
        logger.error("SMTP: recipient refused %s", to_address)
        return False, "smtp_recipient_refused"
    except Exception as exc:
        logger.error("SMTP: unexpected error – %s", exc)
        return False, str(exc)


def _send_sendgrid(cfg, to_address, subject, html_body, text_body) -> tuple[bool, str]:
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Content, To
        sg = sendgrid.SendGridAPIClient(cfg.SENDGRID_API_KEY)
        mail = Mail(
            from_email=cfg.MAIL_FROM,
            to_emails=to_address,
            subject=subject,
            html_content=html_body,
        )
        resp = sg.send(mail)
        if resp.status_code in (200, 202):
            msg_id = resp.headers.get("X-Message-Id", "")
            logger.info("SendGrid: sent to %s | msg_id=%s", to_address, msg_id)
            return True, msg_id
        logger.error("SendGrid: status %s", resp.status_code)
        return False, f"sendgrid_status_{resp.status_code}"
    except ImportError:
        logger.error("sendgrid package not installed.")
        return False, "sendgrid_not_installed"
    except Exception as exc:
        logger.error("SendGrid: %s", exc)
        return False, str(exc)


# ── Email templates ────────────────────────────────────────────────────────

def build_schedule_change_email(
    user_name: str,
    provider: str,
    route_number: str,
    origin: str,
    destination: str,
    old_time: str,
    new_time: str,
    reason: str,
    booking_ref: str,
) -> tuple[str, str, str]:
    """Return (subject, html_body, text_body)."""
    subject = f"TransitNotice – Important Journey Update | {provider} Route {route_number}"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#1a1a2e;max-width:600px;margin:auto;">
      <div style="background:#1e3a5f;padding:20px;text-align:center;">
        <h2 style="color:#fff;margin:0;">🚌 TransitNotice</h2>
        <p style="color:#aed6f1;margin:4px 0;">Smart Public Transport Platform</p>
      </div>
      <div style="padding:24px;background:#f8f9fa;">
        <h3 style="color:#c0392b;">⚠ Important Journey Update</h3>
        <p>Dear <strong>{user_name}</strong>,</p>
        <p>There has been a confirmed change to your upcoming journey.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Transport</td>
              <td style="padding:8px;">{provider}</td></tr>
          <tr><td style="padding:8px;font-weight:bold;">Route</td>
              <td style="padding:8px;">{route_number}</td></tr>
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">From</td>
              <td style="padding:8px;">{origin}</td></tr>
          <tr><td style="padding:8px;font-weight:bold;">To</td>
              <td style="padding:8px;">{destination}</td></tr>
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Previous Departure</td>
              <td style="padding:8px;color:#c0392b;"><s>{old_time}</s></td></tr>
          <tr><td style="padding:8px;font-weight:bold;">Updated Departure</td>
              <td style="padding:8px;color:#27ae60;"><strong>{new_time}</strong></td></tr>
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Booking Ref</td>
              <td style="padding:8px;">{booking_ref}</td></tr>
          <tr><td style="padding:8px;font-weight:bold;">Reason</td>
              <td style="padding:8px;">{reason or 'Schedule updated by operator'}</td></tr>
        </table>
        <p>Please check your booking details before travelling.</p>
        <p style="font-size:12px;color:#888;">
          This notification was generated automatically by TransitNotice based on
          verified data from the transport operator. Always confirm with the
          official provider before travelling.
        </p>
      </div>
      <div style="background:#1e3a5f;padding:12px;text-align:center;">
        <p style="color:#aed6f1;font-size:12px;margin:0;">
          © TransitNotice · Tamil Nadu, India · Manage preferences in your account
        </p>
      </div>
    </body></html>
    """

    text = (
        f"TransitNotice – Journey Update\n\n"
        f"Dear {user_name},\n\n"
        f"There has been a change to your upcoming journey.\n\n"
        f"Transport: {provider}\n"
        f"Route: {route_number}\n"
        f"From: {origin}\n"
        f"To: {destination}\n"
        f"Previous Departure: {old_time}\n"
        f"Updated Departure: {new_time}\n"
        f"Booking Ref: {booking_ref}\n"
        f"Reason: {reason or 'Schedule updated by operator'}\n\n"
        f"Please check your booking before travelling.\n"
    )

    return subject, html, text


def build_booking_confirmation_email(
    user_name: str,
    booking_ref: str,
    provider: str,
    route_number: str,
    origin: str,
    destination: str,
    journey_date: str,
    departure_time: str,
    passenger_count: int,
) -> tuple[str, str, str]:
    subject = f"TransitNotice – Booking Confirmed | {booking_ref}"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#1a1a2e;max-width:600px;margin:auto;">
      <div style="background:#1e3a5f;padding:20px;text-align:center;">
        <h2 style="color:#fff;margin:0;">🚌 TransitNotice</h2>
      </div>
      <div style="padding:24px;background:#f8f9fa;">
        <h3 style="color:#27ae60;">✅ Booking Confirmed</h3>
        <p>Dear <strong>{user_name}</strong>,</p>
        <p>Your booking has been recorded. Please complete payment with the
           official transport provider if not already done.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Booking Ref</td>
              <td style="padding:8px;font-size:18px;"><strong>{booking_ref}</strong></td></tr>
          <tr><td style="padding:8px;font-weight:bold;">Transport</td>
              <td style="padding:8px;">{provider}</td></tr>
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Route</td>
              <td style="padding:8px;">{route_number}</td></tr>
          <tr><td style="padding:8px;font-weight:bold;">From → To</td>
              <td style="padding:8px;">{origin} → {destination}</td></tr>
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Journey Date</td>
              <td style="padding:8px;">{journey_date}</td></tr>
          <tr><td style="padding:8px;font-weight:bold;">Departure</td>
              <td style="padding:8px;">{departure_time}</td></tr>
          <tr><td style="padding:8px;background:#e8f4fd;font-weight:bold;">Passengers</td>
              <td style="padding:8px;">{passenger_count}</td></tr>
        </table>
      </div>
      <div style="background:#1e3a5f;padding:12px;text-align:center;">
        <p style="color:#aed6f1;font-size:12px;margin:0;">
          © TransitNotice · Tamil Nadu, India
        </p>
      </div>
    </body></html>
    """
    text = (
        f"Booking Confirmed – {booking_ref}\n\n"
        f"Dear {user_name},\n"
        f"Transport: {provider} | Route: {route_number}\n"
        f"From: {origin} → To: {destination}\n"
        f"Date: {journey_date} | Departure: {departure_time}\n"
        f"Passengers: {passenger_count}\n"
    )
    return subject, html, text
