# Deployment

The app is designed to be deployed with the frontend and backend hosted separately.

## Backend (Render)

The backend ships with a [`server/Dockerfile`](../server/Dockerfile) and a root [`render.yaml`](../render.yaml) blueprint, so it can be deployed to [Render](https://render.com) as a Dockerized Web Service with no extra setup:

1. Create a new "Blueprint" service on Render pointing at this repository (it will pick up `render.yaml` automatically), or manually create a Web Service with environment "Docker" and Dockerfile path `server/Dockerfile`.
2. Set the `ALLOWED_ORIGINS` environment variable on the service to a comma-separated list of the frontend origin(s) allowed to call the API, e.g. `https://<user>.github.io`.
3. Render builds and deploys automatically on every push to `main`. A `GET /health` endpoint is used for the service's health check.

> **Note:** the free Render tier spins the service down after inactivity, so the first request after idling will be slow (cold start) while the container restarts.

## Frontend (GitHub Pages)

A GitHub Actions workflow ([`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml)) builds the Vite app and publishes `frontend/dist` to GitHub Pages on every push to `main`:

1. Enable GitHub Pages for this repository (Settings → Pages → Source: GitHub Actions).
2. Set a repository variable `VITE_API_BASE_URL` (Settings → Secrets and variables → Actions → Variables) to the deployed Render backend URL, e.g. `https://agt-server.onrender.com`.
3. Push to `main` — the workflow builds and deploys the site automatically.

## Wiring frontend and backend together

Once both are deployed, set `ALLOWED_ORIGINS` on Render to the live frontend URL(s), and `VITE_API_BASE_URL` in the frontend build to the live Render URL, so the two deployments can talk to each other.
