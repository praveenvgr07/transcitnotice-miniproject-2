"""Authentication routes – register, verify, login, logout, forgot/reset password."""
import secrets
import re
import logging
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app,
)
from database.db import execute, fetchone
from models.user_model import (
    create_user, get_user_by_email, get_user_by_mobile,
    update_last_login, set_email_verified, set_mobile_verified, update_password,
    verify_password,
)
from services.email_service import send_email
from services.sms_service import send_otp_sms

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
MOBILE_RE = re.compile(r"^\d{10}$")
MIN_PW = 8


def _flash_errors(form_errors: dict):
    for msg in form_errors.values():
        flash(msg, "danger")


# ── Registration ───────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip().lower()
        mobile    = request.form.get("mobile", "").strip()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        errors = {}
        if len(full_name) < 2:
            errors["full_name"] = "Full name must be at least 2 characters."
        if not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        if not MOBILE_RE.match(mobile):
            errors["mobile"] = "Enter a valid 10-digit Indian mobile number."
        if len(password) < MIN_PW:
            errors["password"] = f"Password must be at least {MIN_PW} characters."
        if password != confirm:
            errors["confirm"] = "Passwords do not match."

        if not errors:
            if get_user_by_email(email):
                errors["email"] = "This email is already registered."
            if get_user_by_mobile(mobile):
                errors["mobile"] = "This mobile number is already registered."

        if errors:
            _flash_errors(errors)
            return render_template("register.html", form=request.form)

        user_id = create_user(full_name, email, mobile, password)
        _send_email_verification(user_id, email, full_name)
        flash(
            "Registration successful! Please check your email to verify your account.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("register.html", form={})


def _send_email_verification(user_id: int, email: str, name: str):
    cfg  = current_app.config_obj
    token = secrets.token_urlsafe(48)
    expires = datetime.utcnow() + timedelta(seconds=cfg.EMAIL_VERIFY_EXPIRY)
    execute(
        """INSERT INTO user_verifications
           (user_id, token_type, token, expires_at)
           VALUES (%s,'email_verify',%s,%s)""",
        (user_id, token, expires),
    )
    verify_url = url_for("auth.verify_email", token=token, _external=True)
    subject = "TransitNotice – Verify Your Email"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;">
      <p>Dear {name},</p>
      <p>Please verify your email address by clicking the link below:</p>
      <p><a href="{verify_url}" style="background:#1e3a5f;color:#fff;
         padding:10px 20px;text-decoration:none;border-radius:4px;">
         Verify Email</a></p>
      <p>This link expires in 24 hours.</p>
    </body></html>
    """
    send_email(cfg, email, subject, html, f"Verify your email: {verify_url}")


@auth_bp.route("/verify-email/<token>")
def verify_email(token: str):
    row = fetchone(
        """SELECT * FROM user_verifications
           WHERE token=%s AND token_type='email_verify'
             AND is_used=0 AND expires_at > NOW()""",
        (token,),
    )
    if not row:
        flash("This verification link is invalid or has expired.", "danger")
        return redirect(url_for("auth.login"))
    set_email_verified(row["user_id"])
    execute("UPDATE user_verifications SET is_used=1 WHERE id=%s", (row["id"],))
    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("auth.login"))


# ── Mobile OTP ────────────────────────────────────────────────────────────

@auth_bp.route("/verify-mobile", methods=["GET", "POST"])
def verify_mobile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user_id = session["user_id"]

    if request.method == "POST":
        action = request.form.get("action")
        if action == "send":
            _send_mobile_otp(user_id)
            flash("OTP sent to your registered mobile number.", "info")
        elif action == "verify":
            otp = request.form.get("otp", "").strip()
            row = fetchone(
                """SELECT * FROM user_verifications
                   WHERE user_id=%s AND token_type='mobile_otp'
                     AND token=%s AND is_used=0 AND expires_at > NOW()""",
                (user_id, otp),
            )
            if not row:
                flash("Invalid or expired OTP.", "danger")
            else:
                set_mobile_verified(user_id)
                execute("UPDATE user_verifications SET is_used=1 WHERE id=%s", (row["id"],))
                flash("Mobile number verified!", "success")
                return redirect(url_for("user.dashboard"))

    return render_template("verify_mobile.html")


def _send_mobile_otp(user_id: int):
    from models.user_model import get_user_by_id
    cfg    = current_app.config_obj
    user   = get_user_by_id(user_id)
    otp    = str(secrets.randbelow(900000) + 100000)
    expires = datetime.utcnow() + timedelta(seconds=cfg.OTP_EXPIRY)
    execute(
        """INSERT INTO user_verifications
           (user_id, token_type, token, expires_at)
           VALUES (%s,'mobile_otp',%s,%s)""",
        (user_id, otp, expires),
    )
    mobile = f"+91{user['mobile']}"
    send_otp_sms(cfg, mobile, otp)


# ── Login / Logout ─────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", form=request.form)

        if not user["is_active"]:
            flash("Your account has been deactivated. Contact support.", "warning")
            return render_template("login.html", form=request.form)

        session.clear()
        session["user_id"]   = user["id"]
        session["user_name"] = user["full_name"]
        session["user_role"] = user["role"]
        update_last_login(user["id"])
        flash(f"Welcome back, {user['full_name']}!", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("user.dashboard"))

    return render_template("login.html", form={})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


# ── Forgot / Reset password ────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user  = get_user_by_email(email)
        if user:
            _send_password_reset(user)
        # Always show success to prevent email enumeration
        flash(
            "If that email is registered, you will receive a password reset link shortly.",
            "info",
        )
        return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")


def _send_password_reset(user: dict):
    cfg   = current_app.config_obj
    token = secrets.token_urlsafe(48)
    expires = datetime.utcnow() + timedelta(seconds=cfg.PASSWORD_RESET_EXPIRY)
    execute(
        """INSERT INTO user_verifications
           (user_id, token_type, token, expires_at)
           VALUES (%s,'password_reset',%s,%s)""",
        (user["id"], token, expires),
    )
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    subject = "TransitNotice – Reset Your Password"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;">
      <p>Dear {user['full_name']},</p>
      <p>Click the link below to reset your password (expires in 1 hour):</p>
      <p><a href="{reset_url}" style="background:#1e3a5f;color:#fff;
         padding:10px 20px;text-decoration:none;border-radius:4px;">
         Reset Password</a></p>
    </body></html>
    """
    send_email(cfg, user["email"], subject, html)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    row = fetchone(
        """SELECT * FROM user_verifications
           WHERE token=%s AND token_type='password_reset'
             AND is_used=0 AND expires_at > NOW()""",
        (token,),
    )
    if not row:
        flash("This link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        if len(password) < MIN_PW:
            flash(f"Password must be at least {MIN_PW} characters.", "danger")
            return render_template("reset_password.html", token=token)
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)
        update_password(row["user_id"], password)
        execute("UPDATE user_verifications SET is_used=1 WHERE id=%s", (row["id"],))
        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
