from datetime import datetime, timezone
from email.message import EmailMessage
import base64
import json
import os
import smtplib
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request, send_from_directory


DEFAULT_LATITUDE = 22.694380
DEFAULT_LONGITUDE = 88.454979
OVERHEAD_RANGE_DEGREES = 5

app = Flask(__name__, static_folder="static", static_url_path="")


def fetch_json(url, timeout=10):
    api_request = Request(url, headers={"User-Agent": "iss-overhead-web-app"})
    with urlopen(api_request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_iss_position():
    data = fetch_json("http://api.open-notify.org/iss-now.json")
    position = data["iss_position"]
    return {
        "latitude": float(position["latitude"]),
        "longitude": float(position["longitude"]),
        "timestamp": data.get("timestamp"),
    }


def get_sun_times(latitude, longitude):
    url = (
        "https://api.sunrise-sunset.org/json"
        f"?lat={latitude}&lng={longitude}&formatted=0"
    )
    data = fetch_json(url)
    results = data["results"]
    sunrise = datetime.fromisoformat(results["sunrise"].replace("Z", "+00:00"))
    sunset = datetime.fromisoformat(results["sunset"].replace("Z", "+00:00"))
    return sunrise, sunset


def is_near_user(iss_position, latitude, longitude):
    return (
        latitude - OVERHEAD_RANGE_DEGREES
        <= iss_position["latitude"]
        <= latitude + OVERHEAD_RANGE_DEGREES
        and longitude - OVERHEAD_RANGE_DEGREES
        <= iss_position["longitude"]
        <= longitude + OVERHEAD_RANGE_DEGREES
    )


def get_visibility(latitude, longitude):
    iss_position = get_iss_position()
    sunrise, sunset = get_sun_times(latitude, longitude)
    now_utc = datetime.now(timezone.utc)
    near_user = is_near_user(iss_position, latitude, longitude)
    is_dark = now_utc <= sunrise or now_utc >= sunset

    return {
        "iss": iss_position,
        "observer": {"latitude": latitude, "longitude": longitude},
        "near_user": near_user,
        "is_dark": is_dark,
        "visible": near_user and is_dark,
        "checked_at": now_utc.isoformat(),
        "sunrise": sunrise.isoformat(),
        "sunset": sunset.isoformat(),
        "range_degrees": OVERHEAD_RANGE_DEGREES,
    }


def send_email_notification(to_email, status):
    sender = os.getenv("ISS_EMAIL_ADDRESS")
    password = os.getenv("ISS_EMAIL_PASSWORD")

    if not sender or not password:
        raise RuntimeError(
            "Set ISS_EMAIL_ADDRESS and ISS_EMAIL_PASSWORD before sending email."
        )

    message = EmailMessage()
    message["Subject"] = "Look up: the ISS may be visible"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        "The ISS is close to your location and it is currently dark.\n\n"
        f"ISS latitude: {status['iss']['latitude']:.2f}\n"
        f"ISS longitude: {status['iss']['longitude']:.2f}\n"
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(sender, password)
        connection.send_message(message)


def send_sms_notification(to_phone, status):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not account_sid or not auth_token or not from_number:
        raise RuntimeError(
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER before sending SMS."
        )

    body = (
        "Look up: the ISS is close to your location and it is dark outside. "
        f"ISS: {status['iss']['latitude']:.2f}, {status['iss']['longitude']:.2f}"
    )
    payload = urlencode(
        {
            "To": to_phone,
            "From": from_number,
            "Body": body,
        }
    ).encode("utf-8")
    credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode(
        "ascii"
    )
    twilio_request = Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urlopen(twilio_request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8")
        raise RuntimeError(f"Twilio SMS failed: {details}") from exc


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/status")
def status():
    try:
        latitude = float(request.args.get("lat", DEFAULT_LATITUDE))
        longitude = float(request.args.get("lng", DEFAULT_LONGITUDE))
        return jsonify(get_visibility(latitude, longitude))
    except (KeyError, URLError, TimeoutError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 502


@app.post("/api/notify")
def notify():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip()
    phone = body.get("phone", "").strip()
    latitude = float(body.get("latitude", DEFAULT_LATITUDE))
    longitude = float(body.get("longitude", DEFAULT_LONGITUDE))

    if not email and not phone:
        return jsonify({"error": "Enter an email address, phone number, or both."}), 400

    try:
        visibility = get_visibility(latitude, longitude)
        if not visibility["visible"]:
            return jsonify(
                {
                    "sent": False,
                    "message": "The ISS is not visible from this location right now.",
                    "status": visibility,
                }
            )

        sent_channels = []
        if email:
            send_email_notification(email, visibility)
            sent_channels.append("email")
        if phone:
            send_sms_notification(phone, visibility)
            sent_channels.append("sms")

        return jsonify(
            {"sent": True, "channels": sent_channels, "status": visibility}
        )
    except (RuntimeError, URLError, TimeoutError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 502


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
