"""SMS service – supports Twilio and MSG91."""
import logging

logger = logging.getLogger(__name__)


def send_sms(cfg, to_number: str, message: str) -> tuple[bool, str]:
    """
    Send an SMS. Returns (success, provider_ref_or_error).
    to_number must include country code, e.g. +919876543210.
    """
    provider = getattr(cfg, "SMS_PROVIDER", "twilio")
    if provider == "msg91":
        return _send_msg91(cfg, to_number, message)
    return _send_twilio(cfg, to_number, message)


def _send_twilio(cfg, to_number: str, message: str) -> tuple[bool, str]:
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException
        client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=cfg.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        logger.info("Twilio SMS sent to %s | SID=%s", to_number, msg.sid)
        return True, msg.sid
    except ImportError:
        logger.error("twilio package not installed.")
        return False, "twilio_not_installed"
    except Exception as exc:
        logger.error("Twilio error: %s", exc)
        return False, str(exc)


def _send_msg91(cfg, to_number: str, message: str) -> tuple[bool, str]:
    try:
        import requests as req
        mobile = to_number.lstrip("+").lstrip("91")
        payload = {
            "sender": cfg.MSG91_SENDER_ID,
            "route": "4",
            "country": "91",
            "sms": [{"message": message, "to": [mobile]}],
        }
        resp = req.post(
            "https://api.msg91.com/api/v2/sendsms",
            json=payload,
            headers={
                "authkey": cfg.MSG91_API_KEY,
                "content-type": "application/json",
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("type") == "success":
            logger.info("MSG91 SMS sent to %s", to_number)
            return True, data.get("message", "ok")
        logger.error("MSG91 error: %s", data)
        return False, str(data)
    except Exception as exc:
        logger.error("MSG91 unexpected error: %s", exc)
        return False, str(exc)


def send_otp_sms(cfg, to_number: str, otp: str, app_name: str = "TransitNotice") -> tuple[bool, str]:
    message = f"{otp} is your {app_name} OTP. Valid for 5 minutes. Do not share."
    return send_sms(cfg, to_number, message)
