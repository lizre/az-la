# Azure Deployment Guide
## Python FastAPI + PostgreSQL + VNet + Key Vault

This guide walks you through every Azure resource by hand so you understand
what each piece does. All commands use the Azure CLI (`az`).

---

## Prerequisites

```bash
# Install Azure CLI (macOS)
brew install azure-cli

# Install Azure CLI (Windows)
winget install Microsoft.AzureCLI

# Log in
az login

# Confirm your subscription
az account show
```

---

## Step 1 — Create a Resource Group

A **resource group** is a logical container for all your Azure resources.
Think of it as a project folder. Everything in this guide goes inside it.

```bash
az group create \
  --name rg-learning \
  --location uksouth
```

> **What you learn:** Resource groups make it easy to see costs, apply
> permissions, and delete everything at once when you're done.

---

## Step 2 — Create a Virtual Network (VNet)

A **VNet** is your private network in Azure. Resources inside it can talk
to each other without going over the public internet.

```bash
az network vnet create \
  --resource-group rg-learning \
  --name vnet-learning \
  --address-prefix 10.0.0.0/16 \
  --subnet-name subnet-app \
  --subnet-prefix 10.0.1.0/24
```

Then add a second subnet for the database:

```bash
az network vnet subnet create \
  --resource-group rg-learning \
  --vnet-name vnet-learning \
  --name subnet-db \
  --address-prefix 10.0.2.0/24
```

> **What you learn:** Subnets segment your network. The app lives in
> `subnet-app`, the DB lives in `subnet-db`. They can talk to each other
> privately, but the DB is not exposed to the internet.

---

## Step 3 — Create Azure Database for PostgreSQL

This is a **managed** PostgreSQL instance — Azure handles backups, patching,
and availability.

```bash
# Create the server
az postgres flexible-server create \
  --resource-group rg-learning \
  --name psql-learning-$(date +%s) \
  --location uksouth \
  --admin-user pgadmin \
  --admin-password "ChangeMe123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --vnet vnet-learning \
  --subnet subnet-db \
  --yes

# Note the server name printed in the output — you'll need it below.
# It looks like: psql-learning-1234567890.postgres.database.azure.com
```

Create the database:

```bash
az postgres flexible-server db create \
  --resource-group rg-learning \
  --server-name <YOUR_SERVER_NAME> \
  --database-name learningdb
```

> **What you learn:** The `--vnet` and `--subnet` flags put the DB inside
> your private network. It has no public IP. Only resources in the same
> VNet can reach it — which is exactly what you want.

---

## Step 4 — Store the Connection String in Key Vault

**Never hardcode secrets.** Key Vault is Azure's secrets manager. Your app
will read the DB password from here at runtime.

```bash
# Create the Key Vault
az keyvault create \
  --resource-group rg-learning \
  --name kv-learning-$(date +%s) \
  --location uksouth

# Store the connection string as a secret
az keyvault secret set \
  --vault-name <YOUR_KEYVAULT_NAME> \
  --name "DATABASE-URL" \
  --value "postgresql://pgadmin:ChangeMe123!@<YOUR_SERVER_NAME>.postgres.database.azure.com/learningdb"
```

> **What you learn:** Secrets live in Key Vault, not in your code or `.env`
> files. App Service can pull them automatically at startup.

---

## Step 5 — Create the App Service Plan + Web App

An **App Service Plan** defines the VM size and pricing tier.
The **Web App** is the actual hosted app running on that plan.

```bash
# Create the plan (B1 = Basic tier, cheapest paid option)
az appservice plan create \
  --resource-group rg-learning \
  --name plan-learning \
  --sku B1 \
  --is-linux

# Create the web app
az webapp create \
  --resource-group rg-learning \
  --plan plan-learning \
  --name <YOUR_APP_NAME> \
  --runtime "PYTHON:3.11"
```

Set the startup command:

```bash
az webapp config set \
  --resource-group rg-learning \
  --name <YOUR_APP_NAME> \
  --startup-file "uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

> **What you learn:** App Service abstracts the server — you don't manage
> VMs or OS. You just deploy code and it runs.

---

## Step 6 — Connect App Service to Your VNet

This lets your app reach the private PostgreSQL DB.

```bash
az webapp vnet-integration add \
  --resource-group rg-learning \
  --name <YOUR_APP_NAME> \
  --vnet vnet-learning \
  --subnet subnet-app
```

> **What you learn:** VNet Integration is how App Service gets access to
> private resources. Without this, the app can't see the DB.

---

## Step 7 — Give the App Access to Key Vault

Enable a **Managed Identity** so the app can authenticate to Key Vault
without any credentials.

```bash
# Enable system-assigned identity
az webapp identity assign \
  --resource-group rg-learning \
  --name <YOUR_APP_NAME>

# Note the "principalId" from the output above, then grant Key Vault access
az keyvault set-policy \
  --name <YOUR_KEYVAULT_NAME> \
  --object-id <PRINCIPAL_ID> \
  --secret-permissions get list
```

Wire the Key Vault secret into the app as an environment variable:

```bash
az webapp config appsettings set \
  --resource-group rg-learning \
  --name <YOUR_APP_NAME> \
  --settings DATABASE_URL="@Microsoft.KeyVault(VaultName=<YOUR_KEYVAULT_NAME>;SecretName=DATABASE-URL)"
```

> **What you learn:** Managed Identity = no passwords for your app to
> authenticate. The `@Microsoft.KeyVault(...)` syntax tells App Service to
> fetch the secret at startup and inject it as an env var.

---

## Step 8 — Set Up GitHub Actions (CI/CD)

Every push to `main` will automatically deploy.

1. Go to **Azure Portal → App Service → Get publish profile**
2. Copy the entire XML content
3. Go to your **GitHub repo → Settings → Secrets and variables → Actions**
4. Add two secrets:
   - `AZURE_WEBAPP_NAME` → your app name (e.g. `my-learning-app`)
   - `AZURE_WEBAPP_PUBLISH_PROFILE` → the XML you copied

The workflow file at `.github/workflows/deploy.yml` is already configured.
Push to `main` and watch it deploy automatically.

> **What you learn:** CI/CD means your deploy process is code, not a manual
> step. Every push is tested and deployed automatically.

---

## Step 9 — Verify It's Working

```bash
# Check the app is running
curl https://<YOUR_APP_NAME>.azurewebsites.net/health

# Create an item
curl -X POST https://<YOUR_APP_NAME>.azurewebsites.net/items \
  -H "Content-Type: application/json" \
  -d '{"name": "My first Azure item", "description": "It works!"}'

# List all items
curl https://<YOUR_APP_NAME>.azurewebsites.net/items

# View the auto-generated API docs
open https://<YOUR_APP_NAME>.azurewebsites.net/docs
```

---

## Step 10 — Explore & Learn

Now that it's running, try poking at the infrastructure:

| Experiment | What you learn |
|---|---|
| Scale the App Service Plan up to P1v3 | Vertical scaling |
| Add a second instance in App Service → Scale out | Horizontal scaling |
| Turn off VNet Integration and watch DB fail | Why private networking matters |
| Rotate the DB password in Key Vault | Secrets rotation without redeployment |
| Check App Service → Log stream | Live logging |
| Break a deploy on purpose (syntax error) | How CI/CD catches failures |

---

## Tear Down (when you're done)

Delete everything at once — this is why resource groups are useful:

```bash
az group delete --name rg-learning --yes --no-wait
```

---

## Cost Estimate

| Resource | Tier | Approx. monthly cost |
|---|---|---|
| App Service Plan | B1 | ~£10 |
| PostgreSQL Flexible Server | Standard_B1ms | ~£12 |
| Key Vault | Standard | ~£0.03/10k ops |
| VNet | — | Free |
| **Total** | | **~£22/month** |

Stop/deallocate resources when not in use to save money.
