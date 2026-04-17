# Azure Deployment Guide

What we actually did to deploy a Python FastAPI app with a PostgreSQL database to Azure Container Apps.

---

## Architecture

```mermaid
graph TD
    User["Browser / User"]
    CA["Container App\naz-la-app\n(eastus)"]
    ACR["Container Registry\nca663d5e252cacr\n(eastus)"]
    DB["PostgreSQL\npsql-la-pub\n(uksouth)"]
    RG["Resource Group: rg-learning"]

    User -->|"HTTPS :443"| CA
    CA -->|"pulls image on deploy"| ACR
    CA -->|"DATABASE_URL over internet\nport 5432 + SSL"| DB

    subgraph RG
        CA
        ACR
        DB
    end
```

**How it fits together:**
- The user opens the app in a browser. The request hits the Container App over HTTPS.
- The Container App runs the FastAPI code inside a Docker container. That container image is stored in the Container Registry and pulled each time you deploy.
- When the app needs to read or write data, it connects to PostgreSQL over the internet using an encrypted connection string stored as an environment variable.

---

## Technology choices

### FastAPI
FastAPI is a Python framework for building web APIs. We used it because:
- It's Python — readable, beginner-friendly, huge ecosystem
- It auto-generates interactive docs at `/docs` so you can test endpoints in the browser without writing any extra code
- It handles the HTTP layer (routing, request parsing, response formatting) so you just write functions

The alternative would be Flask (simpler but fewer features) or Django (more features but much more setup). FastAPI is a good middle ground for learning.

### PostgreSQL
PostgreSQL is a relational database — data is stored in tables with rows and columns, like a spreadsheet, but with the ability to query and relate data across tables. We used it because:
- It's the most popular open-source database and widely used in production
- Azure has a managed version (Flexible Server) that handles backups, patching, and availability for you — you don't run it yourself
- It pairs well with SQLAlchemy, the Python library the app uses to talk to it

The alternative would be a simpler database like SQLite (no server needed, just a file) but that doesn't work well in the cloud where containers can restart and lose local files.

### Why Docker / Container Apps instead of running Python directly
When you deploy to the cloud, you need a consistent way to package your app and its dependencies so it runs the same way everywhere. Docker bundles your code, Python version, and all libraries into a single image. Container Apps runs that image and handles scaling, restarts, and HTTPS for you.

---

## What's running

| Resource | Name | Details |
|---|---|---|
| Container App | `az-la-app` | eastus, public URL |
| Container Apps Environment | `env-learning` | eastus |
| Container Registry | `ca663d5e252cacr` | eastus, stores Docker images |
| PostgreSQL | `psql-la-pub` | uksouth, public access, Burstable B1ms |
| Resource Group | `rg-learning` | holds everything |

**Live URL:** `https://az-la-app.ashysky-c3ba7f70.eastus.azurecontainerapps.io/`

**DB connection string:** `postgresql://pgadmin:ChangeMe123!@psql-la-pub.postgres.database.azure.com/postgres?sslmode=require`

---

## Subscription gotchas (Visual Studio Enterprise)

This subscription has restricted quotas and blocked regions. Things to know before you start:

- **App Service is unavailable** — 0 quota in all regions and tiers. Use Container Apps instead.
- **Some regions are blocked for PostgreSQL** — `eastus` is blocked. `uksouth` works.
- **Azure provider namespaces need registering** — before using a service for the first time, run `az provider register --namespace <name>` and wait for it to say `Registered`.
- **`!` and `@` cause zsh issues in quoted strings** — always use single quotes around values containing these characters, and never split commands across lines with backslashes.

---

## Step 1 — Register providers

Run these once on a new subscription. Each can take a few minutes.

```bash
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.ContainerRegistry
```

Check they're done:

```bash
az provider show --namespace Microsoft.ContainerRegistry --query registrationState
```

---

## Step 2 — Resource group

```bash
az group create --name rg-learning --location uksouth
```

---

## Step 3 — Container Apps environment

```bash
az containerapp env create --name env-learning --resource-group rg-learning --location eastus
```

> `eastus` has Container Apps quota on this subscription. `uksouth` did not at time of writing.

---

## Step 4 — PostgreSQL database

Create with **public access** so Container Apps can reach it. Private networking requires VNet integration which is significantly more complex.

```bash
az postgres flexible-server create --name psql-la-pub --resource-group rg-learning --location uksouth --admin-user pgadmin --admin-password 'ChangeMe123!' --sku-name Standard_B1ms --tier Burstable --storage-size 32 --public-access 0.0.0.0 --yes
```

Add a firewall rule to allow inbound connections:

```bash
az postgres flexible-server firewall-rule create --name psql-la-pub --resource-group rg-learning --rule-name allow-all --start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255
```

> `0.0.0.0` to `255.255.255.255` allows all IPs. Fine for learning — tighten this for production.

---

## Step 5 — Build and push Docker image

Azure Container Registry (ACR) stores your Docker images. The `az acr build` command builds in the cloud — no local Docker needed.

Create the registry (only needed once):

```bash
az acr create --name ca663d5e252cacr --resource-group rg-learning --sku Basic --admin-enabled true
```

Build and push your image:

```bash
az acr build --registry ca663d5e252cacr --image az-la-app:latest .
```

---

## Step 6 — Deploy the app

```bash
az containerapp create --name az-la-app --resource-group rg-learning --environment env-learning --image ca663d5e252cacr.azurecr.io/az-la-app:latest --target-port 8000 --ingress external --registry-server ca663d5e252cacr.azurecr.io
```

Set the database connection string:

```bash
az containerapp update --name az-la-app --resource-group rg-learning --set-env-vars 'DATABASE_URL=postgresql://pgadmin:ChangeMe123!@psql-la-pub.postgres.database.azure.com/postgres?sslmode=require'
```

> Single quotes are required around the value — `!` and `@` break zsh in double quotes.

Enable Application Insights + OpenTelemetry (API traces, per-endpoint latency, and browser page-load telemetry):

```bash
az containerapp update --name az-la-app --resource-group rg-learning --set-env-vars 'APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=<key>;IngestionEndpoint=<endpoint>'
```

---

## Step 7 — Redeploy after code changes

Rebuild the image and force a new revision:

```bash
az acr build --registry ca663d5e252cacr --image az-la-app:latest .
az containerapp update --name az-la-app --resource-group rg-learning --image ca663d5e252cacr.azurecr.io/az-la-app:latest --revision-suffix v2
```

Increment the revision suffix each time (`v2`, `v3`, etc.) to force Container Apps to pull the new image.

---

## Step 8 — Test it

Open in browser:

```
https://az-la-app.ashysky-c3ba7f70.eastus.azurecontainerapps.io/
```

Or hit the API directly:

```bash
curl https://az-la-app.ashysky-c3ba7f70.eastus.azurecontainerapps.io/health
curl https://az-la-app.ashysky-c3ba7f70.eastus.azurecontainerapps.io/items
```

Interactive API docs:

```
https://az-la-app.ashysky-c3ba7f70.eastus.azurecontainerapps.io/docs
```

---

## Tear down

Deletes everything at once:

```bash
az group delete --name rg-learning --yes --no-wait
```

---

## Cost estimate

| Resource | Tier | Approx monthly |
|---|---|---|
| Container Apps | Consumption | ~£0–5 |
| PostgreSQL | Standard_B1ms | ~£12 |
| Container Registry | Basic | ~£4 |
| **Total** | | **~£16–21** |

Container Apps bills per request — if you're not using it, it costs almost nothing.
