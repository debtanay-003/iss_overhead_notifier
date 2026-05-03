# ISS Overhead Notifier

Interactive web version of the ISS overhead notifier. It checks the current ISS
latitude and longitude, compares that with your location, checks whether it is
dark outside, and can send an email when the ISS is visible.

## Run locally

```powershell
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000 in your browser.

## Deploy on Render

Push this project to GitHub, then create a Render Web Service from that repo.

Use these Render settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

The included `render.yaml` can also be used as a Render blueprint.

After deployment, Render will give you a public URL like:

```text
https://iss-overhead-notifier.onrender.com
```

## Optional email alerts

Before using the email button, set these environment variables:

```powershell
$env:ISS_EMAIL_ADDRESS="your.email@gmail.com"
$env:ISS_EMAIL_PASSWORD="your-gmail-app-password"
python app.py
```

Use a Gmail app password instead of your normal Gmail password.

## Optional SMS alerts

SMS alerts use Twilio. Phone numbers should be entered in E.164 format, such as
`+15551234567`.

```powershell
$env:TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:TWILIO_AUTH_TOKEN="your-twilio-auth-token"
$env:TWILIO_FROM_NUMBER="+15551234567"
python app.py
```

If your Twilio account is in trial mode, Twilio requires the recipient phone
number to be verified first.

## Render environment variables

Set these in the Render dashboard under your service's Environment page:

```text
ISS_EMAIL_ADDRESS
ISS_EMAIL_PASSWORD
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
```
