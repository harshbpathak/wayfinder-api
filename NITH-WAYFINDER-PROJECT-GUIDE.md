# NITH Hamirpur Wayfinder

End-to-end project guide for the NIT Hamirpur campus voice wayfinding agent,
API, browser testing frontend, OpenStreetMap routing, Bolna configuration, and
Render deployment.

## 1. What the project does

The system lets a user ask:

> Where is the Vivekananda Lecture Hall Complex?

The application:

1. Receives the place query.
2. Fuzzy-matches it against the NIT Hamirpur location directory.
3. Uses the user's current browser location, or a supplied coordinate.
4. Calculates a route using OpenStreetMap data through OSRM.
5. Returns the destination, distance in kilometres, compass direction, route time,
   an OpenStreetMap link, and route geometry.
6. Draws the route on an interactive OpenStreetMap map.

The same `/locate` API is designed to be called by a Bolna voice agent.

## 2. Current project location

```text
C:\nith-wayfinder-locate-api
```

Important files:

```text
C:\nith-wayfinder-locate-api\main.py
C:\nith-wayfinder-locate-api\locations.json
C:\nith-wayfinder-locate-api\static\index.html
C:\nith-wayfinder-locate-api\requirements.txt
C:\nith-wayfinder-locate-api\render.yaml
C:\nith-wayfinder-locate-api\bolna-system-prompt.txt
C:\nith-wayfinder-locate-api\README.md
C:\nith-wayfinder-locate-api\test_main.py
```

## 3. Architecture

```text
Browser frontend
    │
    ├── Browser GPS permission
    ├── Place query
    └── OpenStreetMap map display
    │
    ▼
FastAPI /locate endpoint
    │
    ├── Fuzzy location matching
    ├── Location coordinates from locations.json
    └── OSRM route request
    │
    ▼
OpenStreetMap + OSRM
    │
    ▼
Distance, compass direction, duration, route geometry

Bolna phone agent ──► same /locate endpoint
```

## 4. Backend API

The backend is a FastAPI application in `main.py`.

### Health endpoint

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "locations_loaded": 12
}
```

### Location endpoint

```http
GET /locate?query=vivekananda%20lecture%20hall%20complex
```

Optional starting coordinates:

```http
GET /locate?query=CSE&origin_lat=31.7017559&origin_lon=76.5228147
```

If no origin is supplied, the API defaults to Gate 1 of NIT Hamirpur.

Example response:

```json
{
  "found": true,
  "name": "Vivekananda Lecture Hall Complex",
  "directions": "About 1.3 kilometres to the north-east, or approximately 3 minutes by route.",
  "confidence": 100.0,
  "candidates": [],
  "maps_link": "https://www.openstreetmap.org/?mlat=31.7074239&mlon=76.5263078#map=19/31.7074239/76.5263078",
  "directions_source": "OpenStreetMap/OSRM",
  "route": {
    "distance_meters": 1330,
    "distance_km": 1.33,
    "duration_minutes": 3,
    "compass_direction": "north-east",
    "geometry": {}
  }
}
```

### API authentication

If `LOCATE_API_KEY` is configured, requests must include:

```http
x-api-key: your-secret
```

For local development, the key can be omitted. For Render and Bolna, use a
long random secret.

## 5. Location directory

`locations.json` contains the starter directory. Each record contains:

- `id`: stable internal identifier
- `name`: display name
- `aliases`: phrases likely to be spoken by callers
- `directions`: optional verified human-written directions
- `latitude` and `longitude`: OpenStreetMap coordinates
- `maps_link`: OpenStreetMap destination link

The starter data currently covers:

- CSE Department
- ECE Department
- Electrical Engineering Department
- Mechanical Engineering Department
- Civil Engineering Department
- Chemical Engineering Department
- Architecture Department
- Vivekananda Lecture Hall Complex
- Central Library
- Administrative Block
- Health Centre
- Sports Complex

Coordinates were obtained from OpenStreetMap data. They must still be checked
against the real campus before treating them as authoritative. Add hostels,
messes, gates, offices, rooms, and other facilities as needed.

## 6. Browser frontend

The frontend is served by FastAPI at `/` from:

```text
C:\nith-wayfinder-locate-api\static\index.html
```

It provides:

- Natural-language place search
- “Use my current location” browser GPS button
- Manual latitude and longitude inputs
- Distance in kilometres
- Compass direction
- Estimated route duration
- Interactive Leaflet map
- Route line from origin to destination
- Origin and destination markers
- OpenStreetMap destination link
- Error and ambiguous-match messages

The map uses Leaflet and OpenStreetMap tiles. OpenStreetMap attribution is
shown on the map.

## 7. Run locally

From PowerShell:

```powershell
cd C:\nith-wayfinder-locate-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

Test the API directly:

```text
http://127.0.0.1:8000/health
```

```text
http://127.0.0.1:8000/locate?query=CSE
```

## 8. Automated verification

Run:

```powershell
cd C:\nith-wayfinder-locate-api
python -m pytest . -q
```

Current verification result:

```text
4 passed
```

The tests cover:

- Health response
- Spoken alias matching
- Unknown-query handling
- API-key enforcement

The frontend root endpoint was also verified to return HTTP 200 and valid HTML.

## 9. OpenStreetMap and OSRM

This project does not require Google Maps billing or a Google API key.

OSRM calculates routes using OpenStreetMap road data. The current default is:

```text
OSRM_URL=https://router.project-osrm.org
OSRM_PROFILE=driving
```

The public OSRM service is free and suitable for testing or a small demo, but
it is best-effort and has no availability guarantee. Avoid excessive traffic.
For a larger or commercial deployment, use a hosted routing provider or run
your own OSRM instance.

OpenStreetMap requires attribution. Keep the attribution displayed in the
frontend and do not remove it.

## 10. Browser current-location behavior

The web application can use the user's real location through the browser's
Geolocation API.

The user must:

1. Open the application over HTTPS.
2. Click “Use my current location”.
3. Allow location access in the browser prompt.

Render provides HTTPS automatically for its service URL.

If permission is denied, the user can enter latitude and longitude manually.

## 11. Voice-agent behavior

The Bolna agent should:

- Call `locate_place` for every campus-location question.
- Never invent directions from its own knowledge.
- Read the returned `directions` in one or two short sentences.
- Ask the caller to choose when candidates are returned.
- Explain that it only supports NIT Hamirpur wayfinding for unrelated questions.

The prompt is stored in:

```text
C:\nith-wayfinder-locate-api\bolna-system-prompt.txt
```

## 12. Bolna custom function configuration

Create a custom function named `locate_place` in Bolna's Tools section.

Use this function definition:

```json
{
  "name": "locate_place",
  "description": "Use this function whenever the caller asks where a NIT Hamirpur campus building, department, hostel, lecture hall, facility, or landmark is located.",
  "pre_call_message": "Let me check that location for you.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The place the caller wants to find, such as CSE department, library, hostel, or lecture hall."
      }
    },
    "required": ["query"]
  },
  "key": "custom_task",
  "value": {
    "method": "GET",
    "param": {
      "query": "%(query)s"
    },
    "url": "https://YOUR-RENDER-APP.onrender.com/locate",
    "headers": {
      "x-api-key": "YOUR_LOCATE_API_KEY"
    }
  }
}
```

The `key` value must remain exactly:

```json
"key": "custom_task"
```

## 13. Phone behavior limitation

A normal phone call does not expose the caller's GPS coordinates to Bolna.

Therefore the current API defaults to NIT Gate 1 when called by Bolna. For
better voice behavior, update the prompt so the agent asks:

> What campus gate, hostel, or building are you starting from?

The Bolna function would then need an optional `origin` parameter and a lookup
table for known campus landmarks. The browser frontend already supports exact
origin coordinates.

## 14. Render deployment

The project includes:

```text
C:\nith-wayfinder-locate-api\render.yaml
```

Recommended Render service settings:

```text
Environment: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set these Render environment variables:

```text
LOCATE_API_KEY=generate-a-long-random-secret
OSRM_URL=https://router.project-osrm.org
OSRM_PROFILE=driving
OSM_USER_AGENT=NITH-Wayfinder/1.0
```

After deployment, verify:

```text
https://YOUR-APP.onrender.com/health
```

Then open:

```text
https://YOUR-APP.onrender.com/
```

## 15. Required actions from the owner

You must still complete these account and real-world tasks:

- Create or select the GitHub repository.
- Push the contents of `C:\nith-wayfinder-locate-api`.
- Create the Render Web Service or Blueprint.
- Set the Render environment variables.
- Create the Bolna account.
- Create the Bolna voice agent.
- Paste the system prompt.
- Add the custom `locate_place` function.
- Attach or provision a Bolna phone number.
- Connect the phone number to the agent.
- Test the Bolna playground.
- Make a real phone call.
- Verify every destination coordinate and route on-site.
- Add any missing hostels, messes, offices, rooms, and facilities.

These steps require your accounts, credentials, phone, and local campus
knowledge and cannot safely be completed by code alone.

## 16. Security notes

- Never commit `LOCATE_API_KEY` to GitHub.
- Never commit a permanent secret inside the public frontend.
- The frontend API-key input is for temporary testing only.
- Keep the API key in Render and Bolna configuration.
- Restrict or rotate the API key if it is exposed.
- Do not use fabricated directions for emergency, medical, or safety-critical
  navigation.

## 17. Current status

The project is locally working end to end:

```text
Browser query
  → FastAPI matching
  → OSRM route calculation
  → distance and compass direction
  → interactive OpenStreetMap route map
```

The production phone product becomes fully live after Render deployment,
Bolna configuration, phone-number setup, and on-site verification of the
campus data.

## 18. Reference documentation

- [OSRM API documentation](https://project-osrm.org/docs/)
- [OSRM API usage policy](https://github-wiki-see.page/m/Project-OSRM/osrm-backend/wiki/Api-usage-policy)
- [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/)
- [Bolna custom function documentation](https://www.bolna.ai/docs/tool-calling/custom-function-calls)
- [Bolna inbound agent documentation](https://www.bolna.ai/docs/api-reference/inbound/agent)
- [NIT Hamirpur infrastructure information](https://www.nith.ac.in/planning-works)
