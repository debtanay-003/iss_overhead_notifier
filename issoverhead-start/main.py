import requests
from datetime import datetime
import smtplib
import time
import os

MY_EMAIL = os.getenv("ISS_EMAIL_ADDRESS")
MY_PASSWORD = os.getenv("ISS_EMAIL_PASSWORD")
MY_LAT = 22.694380 # Your latitude
MY_LONG = 88.454979 # Your longitude

def is_iss_overhead():
    response = requests.get(url="http://api.open-notify.org/iss-now.json")
    response.raise_for_status()
    data = response.json()

    iss_latitude = float(data["iss_position"]["latitude"])
    iss_longitude = float(data["iss_position"]["longitude"])

    #Your position is within +5 or -5 degrees of the ISS position.
    if MY_LAT-5 <= iss_latitude <= MY_LAT+5 and MY_LONG-5 <= iss_longitude <= MY_LONG+5:
        return True

def is_night():
    parameters = {
        "lat": MY_LAT,
        "lng": MY_LONG,
        "formatted": 0,
    }

    response = requests.get("https://api.sunrise-sunset.org/json", params=parameters)
    response.raise_for_status()
    data = response.json()
    sunrise = int(data["results"]["sunrise"].split("T")[1].split(":")[0])
    sunset = int(data["results"]["sunset"].split("T")[1].split(":")[0])

    time_now = datetime.now().hour

    if time_now >= sunset or time_now <= sunrise:
        return True

def main():
    while True:
        time.sleep(60)
        if is_iss_overhead() and is_night():
            if not MY_EMAIL or not MY_PASSWORD:
                raise RuntimeError("Set ISS_EMAIL_ADDRESS and ISS_EMAIL_PASSWORD first.")
            with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                connection.starttls()
                connection.login(MY_EMAIL, MY_PASSWORD)
                connection.sendmail(
                    from_addr=MY_EMAIL,
                    to_addrs=MY_EMAIL,
                    msg="Subject: Look up\n\nThe ISS is above you in the sky."
                )


if __name__ == "__main__":
    main()

#If the ISS is close to my current position
# and it is currently dark
# Then send me an email to tell me to look up.
# BONUS: run the code every 60 seconds.
