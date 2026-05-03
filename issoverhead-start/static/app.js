const form = document.querySelector("#locationForm");
const notifyForm = document.querySelector("#notifyForm");
const useLocationButton = document.querySelector("#useLocationButton");
const message = document.querySelector("#message");
const defaultLocation = [22.69438, 88.454979];

const fields = {
  latitude: document.querySelector("#latitude"),
  longitude: document.querySelector("#longitude"),
  email: document.querySelector("#email"),
  visibilityText: document.querySelector("#visibilityText"),
  issPosition: document.querySelector("#issPosition"),
  checkedAt: document.querySelector("#checkedAt"),
  nearUser: document.querySelector("#nearUser"),
  isDark: document.querySelector("#isDark"),
  sunrise: document.querySelector("#sunrise"),
  sunset: document.querySelector("#sunset"),
  phone: document.querySelector("#phone"),
};

const userIcon = L.divIcon({
  className: "",
  html: '<span class="map-pin user" aria-label="Your selected location"></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const issIcon = L.divIcon({
  className: "",
  html: '<span class="map-pin iss" aria-label="ISS current location"></span>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const map = L.map("map", {
  worldCopyJump: true,
  zoomControl: true,
}).setView(defaultLocation, 4);

setTimeout(() => {
  map.invalidateSize();
}, 100);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const userMarker = L.marker(defaultLocation, {
  icon: userIcon,
  draggable: true,
  title: "Your selected location",
}).addTo(map);

const issMarker = L.marker([0, 0], {
  icon: issIcon,
  title: "ISS current location",
}).addTo(map);

function formatTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function yesNo(value) {
  return value ? "Yes" : "No";
}

function readLocation() {
  return {
    latitude: Number(fields.latitude.value),
    longitude: Number(fields.longitude.value),
  };
}

function setSelectedLocation(latitude, longitude, shouldPan = true) {
  fields.latitude.value = latitude.toFixed(6);
  fields.longitude.value = longitude.toFixed(6);
  userMarker.setLatLng([latitude, longitude]);

  if (shouldPan) {
    map.panTo([latitude, longitude]);
  }
}

async function refreshStatus() {
  const { latitude, longitude } = readLocation();
  message.textContent = "Checking the ISS position...";

  const response = await fetch(`/api/status?lat=${latitude}&lng=${longitude}`);
  const status = await response.json();

  if (!response.ok || status.error) {
    throw new Error(status.error || "Unable to check ISS visibility.");
  }

  fields.visibilityText.textContent = status.visible
    ? "Visible now"
    : "Not visible yet";
  fields.issPosition.textContent = `${status.iss.latitude.toFixed(2)}, ${status.iss.longitude.toFixed(2)}`;
  fields.checkedAt.textContent = formatTime(status.checked_at);
  fields.nearUser.textContent = yesNo(status.near_user);
  fields.isDark.textContent = yesNo(status.is_dark);
  fields.sunrise.textContent = formatTime(status.sunrise);
  fields.sunset.textContent = formatTime(status.sunset);

  userMarker.setLatLng([latitude, longitude]);
  issMarker.setLatLng([status.iss.latitude, status.iss.longitude]);

  message.textContent = status.visible
    ? "The ISS is close and it is dark outside. Look up."
    : "The ISS is not visible from this location right now.";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await refreshStatus();
  } catch (error) {
    message.textContent = error.message;
  }
});

notifyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const { latitude, longitude } = readLocation();

  try {
    message.textContent = "Checking before sending...";
    const response = await fetch("/api/notify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: fields.email.value,
        phone: fields.phone.value,
        latitude,
        longitude,
      }),
    });
    const result = await response.json();

    if (!response.ok || result.error) {
      throw new Error(result.error || "Unable to send notification.");
    }

    message.textContent = result.sent
      ? `Alert sent by ${result.channels.join(" and ")}.`
      : result.message;
  } catch (error) {
    message.textContent = error.message;
  }
});

useLocationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    message.textContent = "Geolocation is not available in this browser.";
    return;
  }

  message.textContent = "Getting your browser location...";
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      setSelectedLocation(position.coords.latitude, position.coords.longitude);
      try {
        await refreshStatus();
      } catch (error) {
        message.textContent = error.message;
      }
    },
    () => {
      message.textContent = "Location permission was not granted.";
    }
  );
});

map.on("click", async (event) => {
  setSelectedLocation(event.latlng.lat, event.latlng.lng, false);

  try {
    await refreshStatus();
  } catch (error) {
    message.textContent = error.message;
  }
});

userMarker.on("dragend", async () => {
  const location = userMarker.getLatLng();
  setSelectedLocation(location.lat, location.lng, false);

  try {
    await refreshStatus();
  } catch (error) {
    message.textContent = error.message;
  }
});

refreshStatus().catch((error) => {
  message.textContent = error.message;
});

setInterval(() => {
  refreshStatus().catch((error) => {
    message.textContent = error.message;
  });
}, 60000);
