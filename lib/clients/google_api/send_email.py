#!/usr/bin/env -S uv run --quiet --with google-auth --with google-api-python-client --with python-dotenv
"""Send emails via Gmail API using service account with domain delegation."""

import base64
import json
import os
import re
import sys
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()


def _build_gmail_service(impersonate_user: str):
    """Build an authenticated Gmail API service with domain delegation."""
    raw = os.environ.get("GOOGLE__SERVICE_ACCOUNT", "")
    if not raw:
        raise RuntimeError("GOOGLE__SERVICE_ACCOUNT not set in environment")
    sa_info = json.loads(raw)
    sa_info.pop("subject", None)
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://mail.google.com/"],
        subject=impersonate_user,
    )
    return build("gmail", "v1", credentials=creds)


def _ordinal_suffix(day: int) -> str:
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def _prompt_opens_datetime() -> str:
    """Prompt for registration opens date/time and return a formatted string.

    Returns "Today, Month Dth at Xpm ET" if the date is today,
    otherwise "DayOfWeek, Month Dth at Xpm ET".
    """
    today = date.today()

    while True:
        date_input = input("Registration opens date (e.g. 'today', 'June 9', '2026-06-09'): ").strip()
        if not date_input:
            print("  Date is required.")
            continue
        if date_input.lower() == "today":
            parsed_date = today
            break
        cleaned = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", date_input, flags=re.IGNORECASE).strip()
        for fmt in ("%Y-%m-%d", "%B %d", "%b %d", "%m/%d/%Y", "%m/%d"):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                parsed_date = parsed.replace(year=today.year).date()
                break
            except ValueError:
                continue
        else:
            print(f"  Could not parse '{date_input}'. Try 'today', 'June 9', or '2026-06-09'.")
            continue
        break

    while True:
        time_input = input("Registration opens time ET (e.g. '7pm', '7:30pm'): ").strip()
        if not time_input:
            print("  Time is required.")
            continue
        break

    day_num = parsed_date.day
    month_day = f"{parsed_date.strftime('%B')} {day_num}{_ordinal_suffix(day_num)}"
    date_part = f"Today, {month_day}" if parsed_date == today else f"{parsed_date.strftime('%A')}, {month_day}"

    return f"{date_part} at {time_input} ET"


def get_gmail_signature(gmail_service, email: str) -> str | None:
    """Fetch the default Gmail signature for the authenticated user.

    Args:
        gmail_service: Authenticated Gmail API service resource
        email: Email address to fetch signature for (actual email, not "me")

    Returns:
        HTML signature string, or None if no signature configured

    Note:
        Requires mail.google.com scope to read signature settings.
    """
    from googleapiclient.errors import HttpError

    try:
        send_as = gmail_service.users().settings().sendAs().get(
            userId="me",
            sendAsEmail=email
        ).execute()

        return send_as.get("signature", "")
    except HttpError as e:
        if e.resp.status == 404:
            return None
        if e.resp.status == 403:
            print("⚠️  Missing scope to read signature. Need: mail.google.com")
        else:
            print(f"⚠️  Could not fetch signature: {e.reason}")
        return None
    except Exception as e:
        print(f"⚠️  Could not fetch signature: {e}")
        return None


def create_veteran_email_message(
    recipients: list[str],
    sport: str,
    day: str,
    division: str,
    season: str,
    year: str,
    leadership_email: str,
    opens_datetime: str,
    reply_to: str | None = None,
    cc: str | None = None,
    signature_html: str | None = None,
) -> dict:
    """Create a MIME message for veteran eligibility notification.

    Args:
        recipients: List of BCC recipient email addresses
        sport: Sport name (e.g. "Kickball")
        day: Day of week (e.g. "Saturday")
        division: Division name
        season: Season name (e.g. "Spring")
        year: Year (e.g. "2026")
        leadership_email: Leadership email for replies
        opens_datetime: Formatted string for when registration opens (e.g. "Today, June 1st at 7pm ET")
        reply_to: Reply-to address (defaults to leadership_email)
        cc: Optional CC recipient
        signature_html: Gmail signature HTML (fetched from account settings)

    Returns:
        Message dict ready for Gmail API send

    Note:
        From/To headers are set by Gmail based on the authenticated user (service account subject).
        The message is sent as the impersonated user.
    """
    reply_to = reply_to or leadership_email

    subject = (
        f"Big Apple {sport.capitalize()} - Veteran Eligibility for "
        f"{season.capitalize()} {year} - {day.capitalize()} - {division.capitalize()} Division"
    )

    product_handle = f"{year}-{season.lower()}-{sport.lower()}-{day.lower()}-{division.lower()}div"

    def create_login_hyperlink_for_product(product_handle: str, display_text: str) -> str:
        login_url_base = "https://www.bigapplerecsports.com/customer_authentication/login"
        return_to_product_param = f"return_to=%2Fproducts%2F{product_handle}&locale=en"
        return f"<a href='{login_url_base}?{return_to_product_param}' target='_blank'>{display_text}</a>"

    html_body = f"""
    <p>Hello!</p>
    <p>You met last season's attendance requirements in <b>{day.capitalize()} {sport.capitalize()}</b> and are therefore eligible
    to register early as a <u>veteran</u> for the upcoming <b>{season.capitalize()} {year}</b> season. <br>
    The Veteran Registration window for {day.capitalize()} {sport.capitalize()} opens <u>{opens_datetime}</u>.</p>
    for the <b>{season.capitalize()} {year}</b> season of <b>{day.capitalize()} {sport.capitalize()} ({division.capitalize()} Division)</b>.</p>

    <p> In order to register during the Veteran window, you must be <i>logged in</i> to your Shopify account
    to add to cart and checkout - your logged-in email address is what our system uses to validate eligibility and unlock access.
    If this is your first season as a vet, we recommend signing in <i>before</i> your registration period starts, in case you experience any issues;
    we may not be able to help right at registration time.</p>

    <p>{create_login_hyperlink_for_product(product_handle, "This hyperlink")} <i>should</i> redirect straight to the {day.capitalize()} {sport.capitalize()} registration page after you login")</p>

    <p>(If it doesn't please forgive us - this is new, and an attempt to be helpful!) You can also go to <a href='https://bigapplerecsports.com' target='_blank'>Our home page (bigapplerecsports.com)</a>, log in at top right,
    navigate back to <b>Shop</b>, then to Registration > {sport.capitalize()} Registration > your division, and get to it from there.)

    <p>Please note that 1) veteran status <i>does not guarantee your spot</i> — you must register successfully
    while spots are still available, and 2) it is not transferable or deferrable,
    unfortunately. We're trying to be as fair as possible to as many people as possible.</p>

    <p>If you have any questions, please reach out to
    <a style='color:blue' href='mailto:{leadership_email}'>{leadership_email}</a></p>

    {f"<br><br>{signature_html}" if signature_html else ""}
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["Bcc"] = ", ".join(recipients)
    message["Reply-To"] = reply_to
    if cc:
        message["Cc"] = cc

    html_part = MIMEText(html_body, "html")
    message.attach(html_part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_veteran_emails(
    recipients: list[str],
    sport: str,
    day: str,
    division: str,
    season: str,
    year: str,
    leadership_email: str,
    opens_datetime: str,
    impersonate_user: str = "web@bigapplerecsports.com",
) -> None:
    """Send a single veteran eligibility email with all recipients in BCC.

    Args:
        recipients: List of recipient email addresses (all in BCC)
        sport: Sport name
        day: Day of week
        division: Division name
        season: Season name
        year: Year
        leadership_email: Leadership email for reply-to and CC
        opens_datetime: Formatted registration opens string (e.g. "Today, June 8th at 7pm ET")
        impersonate_user: Workspace user email to impersonate (must have delegation)

    Note:
        The email will be sent FROM the impersonated user's email address.
        The service account must have domain-wide delegation for this user.
    """
    print(f"🔐 Building Gmail service (impersonating {impersonate_user})...")
    gmail = _build_gmail_service(impersonate_user)

    print("✍️  Fetching Gmail signature...")
    signature_html = get_gmail_signature(gmail, impersonate_user)
    if signature_html:
        print(f"✅ Using signature from {impersonate_user}")
    else:
        print(f"⚠️  No signature configured for {impersonate_user}")

    def _build_message(target_recipients: list[str], cc: str | None) -> dict:
        return create_veteran_email_message(
            recipients=target_recipients,
            sport=sport,
            day=day,
            division=division,
            season=season,
            year=year,
            leadership_email=leadership_email,
            opens_datetime=opens_datetime,
            reply_to=leadership_email,
            cc=cc,
            signature_html=signature_html,
        )

    send_test = input(f"\n📧 Send test email to {impersonate_user} first? [Y/n]: ").strip().lower()
    if send_test not in ("n", "no"):
        test_message = _build_message([impersonate_user], cc=None)
        gmail.users().messages().send(userId="me", body=test_message).execute()
        print(f"✅ Test email sent to {impersonate_user}")

        confirm = input(f"\n📧 Confirm send to {len(recipients)} recipients? [Y/n]: ").strip().lower()
        if confirm in ("n", "no"):
            print("Skipping full send.")
            return

    print(f"📤 Sending email to {len(recipients)} recipients (BCC)...")
    message = _build_message(recipients, cc=leadership_email)
    gmail.users().messages().send(userId="me", body=message).execute()

    print(f"✅ Successfully sent veteran eligibility email to {len(recipients)} recipients")


if __name__ == "__main__":
    if len(sys.argv) < 7:
        print(
            "Usage: send_email.py <sport> <day> <division> <season> <year> "
            "<leadership_email> [email1] [email2] ..."
        )
        print("Example: send_email.py Kickball Monday Open Spring 2026 "
              "joe@bigapplerecsports.com player1@example.com player2@example.com")
        sys.exit(1)

    sport = sys.argv[1]
    day = sys.argv[2]
    division = sys.argv[3]
    season = sys.argv[4]
    year = sys.argv[5]
    leadership_email = sys.argv[6]
    recipient_emails = sys.argv[7:]

    if not recipient_emails:
        print("❌ No recipient emails provided")
        sys.exit(1)

    send_veteran_emails(
        recipients=recipient_emails,
        sport=sport,
        day=day,
        division=division,
        season=season,
        year=year,
        leadership_email=leadership_email,
        opens_datetime=_prompt_opens_datetime(),
    )
