# NITH Wayfinder voice agent

This repository contains the lookup API used by a Bolna phone agent. The API
fuzzy-matches a caller's transcript against `locations.json` and returns a
short, structured result that the voice agent can read aloud.

## Run locally

```powershell
cd C:\nith-wayfinder-locate-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Check `http://127.0.0.1:8000/health`, then try
`http://127.0.0.1:8000/locate?query=CSE`.

Open `http://127.0.0.1:8000/` for the browser-based API tester. After Render
deployment, the same tester will be available at your Render service URL.

Run tests with `python -m pytest . -q`.

## React frontend

The browser application is implemented in `frontend/` with React and
React-Leaflet. The compiled files in `static/` are served by FastAPI, so the
same Render service hosts both the frontend and the API.

To change the frontend:

```powershell
cd C:\nith-wayfinder-locate-api\frontend
npm install
npm run build
```

Commit both `frontend/` and the rebuilt `static/` directory. The build bundles
React and Leaflet, avoiding a runtime dependency on a Leaflet CDN script.

## Deployment

Connect this directory's repository to Render as a Blueprint. Render reads
`render.yaml`; set `LOCATE_API_KEY` to a long random secret and configure the
same value in Bolna's function header `x-api-key`.

The directory now includes OpenStreetMap coordinates for the 12 starter
locations. `/locate` uses the free OSRM routing service to calculate a short
route summary from NIT Gate 1 by default. You can provide a different origin
with `origin_lat` and `origin_lon`. Set `OSRM_URL` and `OSRM_PROFILE` in the
environment if you later move to a self-hosted OSRM instance. The public OSRM
demo server is best-effort and must not be overused; keep caching/rate limits
in mind for a public launch.

The response includes an OpenStreetMap link and `directions_source`. The
coordinates were read from OpenStreetMap and should still be checked on site.
If a route is unavailable, the API returns no fabricated directions. Add a
verified human-readable fallback to `directions` before relying on the service
for safety-critical navigation. OpenStreetMap attribution is required.

## Bolna function contract

Create a GET function named `locate_place` pointing to `/locate`, map its
required `query` string argument to the query parameter, and send the
`x-api-key` header. The function result has this shape:

```json
{"found":true,"name":"...","directions":"...","confidence":95.0,"candidates":[]}
```

The agent should call this function for every campus-location question, read
verified directions in no more than two short sentences, and ask the caller
to choose from `candidates` when the result is ambiguous.
