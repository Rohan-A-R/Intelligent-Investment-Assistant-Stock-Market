# Hosting Your Django Application on Azure App Service

This guide will walk you through the process of deploying your Django application to Azure App Service using the Azure Portal. Azure App Service provides a fully managed platform for hosting web applications, making it an excellent choice for Django projects.

## Table of Contents
1.  [Prerequisites](#prerequisites)
2.  [Application Preparation](#application-preparation)
    *   [Modify settings.py](#modify-settingspy)
    *   [Configure Static Files](#configure-static-files)
    *   [Database Configuration](#database-configuration)
    *   [Handle API Keys Securely](#handle-api-keys-securely)
    *   [Gunicorn Setup](#gunicorn-setup)
3.  [Azure Portal Steps](#azure-portal-steps)
    *   [Create a Resource Group](#create-a-resource-group)
    *   [Create an Azure Database for PostgreSQL](#create-an-azure-database-for-postgresql)
    *   [Create an Azure App Service](#create-an-azure-app-service)
    *   [Configure App Service Settings](#configure-app-service-settings)
4.  [Deploying Your Code](#deploying-your-code)
    *   [Using Local Git Deployment](#using-local-git-deployment)
    *   [Pushing Code to Azure](#pushing-code-to-azure)
5.  [Post-Deployment Steps](#post-deployment-steps)
    *   [Run Database Migrations](#run-database-migrations)
    *   [Collect Static Files](#collect-static-files)
6.  [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

Before you begin, ensure you have the following:

*   An Azure account with an active subscription.
*   Azure CLI installed (optional, but useful for managing resources).
*   Git installed on your local machine.
*   Python and pip installed.
*   Your Django application code ready.

## 2. Application Preparation

Before deploying, you need to make some adjustments to your Django application to ensure it runs correctly in a production environment like Azure App Service.

### Modify settings.py

Open `iia_Core/settings.py` and make the following changes:

*   **`DEBUG = False`**: In a production environment, `DEBUG` should always be `False` for security and performance reasons.

    ```python
    # Before
    # DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # After (ensure this is False in production)
    DEBUG = False
    ```

*   **`ALLOWED_HOSTS`**: This setting defines a list of host/domain names that your Django site can serve. When deploying to Azure, you'll need to add your App Service's domain name (e.g., `your-app-name.azurewebsites.net`).

    ```python
    # Before
    # ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

    # After (add your Azure App Service domain)
    ALLOWED_HOSTS = ['.azurewebsites.net', '127.0.0.1'] # Add your custom domain if you have one
    ```
    **Note**: For `ALLOWED_HOSTS`, it's best practice to retrieve this from environment variables in production. However, for simplicity in this guide, we'll hardcode `.azurewebsites.net`. You can later change this to `os.environ.get('ALLOWED_HOSTS', '').split(',')` and set the `ALLOWED_HOSTS` environment variable in Azure.

*   **`SECRET_KEY`**: Ensure your `SECRET_KEY` is loaded from an environment variable and is kept secret.

    ```python
    # Before (using a default value)
    # SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-x+muavw&%4lu=3^8phte(i=1m3s(j6x6*bm)m93b#=oh#q(4^6')

    # After (ensure it's always from an environment variable in production)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ImproperlyConfigured("The SECRET_KEY environment variable is not set.")
    ```
    You'll need to add `from django.core.exceptions import ImproperlyConfigured` at the top of your `settings.py` if it's not already there.

### Configure Static Files

Your `settings.py` already includes `whitenoise` for static files, which is excellent for production. Ensure `STATIC_ROOT` is correctly defined.

```python
# In your settings.py
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # This is already correct
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' # This is already correct
```

### Database Configuration

Your `settings.py` is already set up to use `dj_database_url` if `DATABASE_URL` is present in the environment, which is the recommended way for Azure.

```python
# In your settings.py
import dj_database_url
# ...
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
    }
else:
    # Your local development database configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'iia_db',
            'USER': 'postgres',
            'PASSWORD': 'Rohan@2002',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
```
When you create your PostgreSQL database in Azure, you will get a connection string that you will set as the `DATABASE_URL` environment variable in your App Service.

### Handle API Keys Securely

The `README.md` and `settings.py` indicate that API keys are stored in `iia_Core/api_keys.py`. For production, it's crucial to keep these out of your codebase and use environment variables.

1.  **Remove `api_keys.py` from version control**: Add `iia_Core/api_keys.py` to your `.gitignore` file if it's not already there.
2.  **Load API keys from environment variables**: Modify `iia_Core/api_keys.py` (or directly in `settings.py` or relevant views) to load these keys from environment variables.

    **Example for `iia_Core/api_keys.py` (after modification):**
    ```python
    import os

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT = os.environ.get('REDDIT_USER_AGENT')

    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
    ```
    You will set these environment variables in your Azure App Service settings.

### Gunicorn Setup

Azure App Service for Python applications typically expects a `gunicorn` command to start your application. Your project's `wsgi.py` is already configured for this. You'll specify the Gunicorn command in the App Service's startup command.

The command will typically look like:
`gunicorn iia_Core.wsgi --bind 0.0.0.0 --timeout 600`

---

## 3. Azure Portal Steps

This section guides you through creating and configuring the necessary resources in the Azure Portal.

### Create a Resource Group

A resource group is a logical container for Azure resources. It helps you manage and organize your Azure assets.

1.  Go to the [Azure Portal](https://portal.azure.com/).
2.  Search for `Resource groups` in the search bar at the top.
3.  Click on `Create`.
4.  **Subscription**: Select your Azure subscription.
5.  **Resource group name**: Enter a unique name for your resource group (e.g., `iia-resource-group`).
6.  **Region**: Choose a region close to your users (e.g., `East US`).
7.  Click `Review + create`, then `Create`.

### Create an Azure Database for PostgreSQL

Your Django application uses PostgreSQL. We'll create a flexible server instance for your database.

1.  In the Azure Portal, search for `Azure Database for PostgreSQL`.
2.  Click `Create`.
3.  Select `Flexible server` and click `Create`.
4.  **Basics Tab**:
    *   **Project details**:
        *   **Subscription**: Your Azure subscription.
        *   **Resource group**: Choose the resource group you created (e.g., `iia-resource-group`).
    *   **Server details**:
        *   **Server name**: Enter a unique name for your PostgreSQL server (e.g., `iia-postgres-server`).
        *   **Region**: Select the same region as your resource group.
        *   **PostgreSQL version**: Choose a version (e.g., `16`).
        *   **Workload type**: Select `Development` or `Production` based on your needs.
        *   **Compute + storage**: Choose a suitable tier (e.g., `Burstable` for development/testing).
    *   **Administrator account**:
        *   **Administrator username**: Enter a username (e.g., `django_admin`).
        *   **Password**: Set a strong password.
        *   **Confirm password**: Confirm the password.
5.  **Networking Tab**:
    *   **Connectivity method**: Select `Public access (allowed IP addresses)`. This is simpler for initial setup. For production, consider `Private access (VNet integration)`.
    *   **Add current client IP address**: Click this to add your current public IP address to the firewall rules. This allows you to connect to the database from your local machine.
    *   **Allow public access from any Azure service within Azure to this server**: Check this box. This is crucial for your App Service to connect to the database.
6.  Click `Review + create`, then `Create`.

    **Important**: Once the database is deployed, navigate to its overview page. Under `Settings`, click on `Connection strings`. Copy the `ADO.NET` connection string. It will look something like this:
    `Host=your-postgres-server.postgres.database.azure.com;Database=your_database_name;Username=your_username;Password={your_password};Ssl Mode=Require;`
    You will use this to construct your `DATABASE_URL` environment variable.

### Create an Azure App Service

This is where your Django application code will run.

1.  In the Azure Portal, search for `App Services`.
2.  Click `Create`.
3.  **Basics Tab**:
    *   **Project details**:
        *   **Subscription**: Your Azure subscription.
        *   **Resource Group**: Select the resource group you created (e.g., `iia-resource-group`).
    *   **Instance Details**:
        *   **Name**: Enter a unique name for your web app (e.g., `iia-django-app`). This will be part of your URL (`iia-django-app.azurewebsites.net`).
        *   **Publish**: Select `Code`.
        *   **Runtime stack**: Select `Python 3.10` (or the version you are using).
        *   **Operating System**: Select `Linux`.
        *   **Region**: Select the same region as your resource group and database.
        *   **App Service Plan**: Click `Create new`.
            *   **App Service Plan name**: Enter a name (e.g., `iia-app-service-plan`).
            *   **Sku and size**: Choose a suitable pricing tier (e.g., `B1` for Basic, `S1` for Standard). For development, `B1` might suffice.
4.  **Deployment Tab**:
    *   **Continuous Deployment**: For now, you can leave this disabled. We will set up local Git deployment later.
5.  Click `Review + create`, then `Create`.

### Configure App Service Settings

After your App Service is created, you need to configure its settings, including environment variables and the startup command.

1.  Navigate to your newly created App Service in the Azure Portal.
2.  In the left-hand menu, under `Settings`, click on `Configuration`.
3.  **Application settings**:
    *   Click `New application setting` to add the following:
        *   **`SECRET_KEY`**: Use a strong, randomly generated string. You can generate one using `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`.
        *   **`DATABASE_URL`**: Construct this from your PostgreSQL connection string. It should look like:
            `postgres://your_username:your_password@your-postgres-server.postgres.database.azure.com:5432/your_database_name?sslmode=require`
            Replace `your_username`, `your_password`, `your-postgres-server.postgres.database.azure.com`, and `your_database_name` with your actual values. Ensure `sslmode=require` is included.
        *   **`GEMINI_API_KEY`**: Your Gemini API key.
        *   **`NEWS_API_KEY`**: Your News API key.
        *   **`REDDIT_CLIENT_ID`**: Your Reddit Client ID.
        *   **`REDDIT_CLIENT_SECRET`**: Your Reddit Client Secret.
        *   **`REDDIT_USER_AGENT`**: Your Reddit User Agent.
        *   **`SOCIAL_AUTH_GOOGLE_OAUTH2_KEY`**: Your Google OAuth2 Client ID.
        *   **`SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET`**: Your Google OAuth2 Client Secret.
        *   **`WEBSITES_ENABLE_APP_SERVICE_STORAGE`**: Set this to `False`. This is important for performance and to avoid issues with static files.
    *   Click `Save`.
4.  **General settings**:
    *   Scroll down to `Startup Command`.
    *   Enter the Gunicorn command:
        `gunicorn iia_Core.wsgi --bind 0.0.0.0 --timeout 600`
    *   Click `Save`.

---

## 4. Deploying Your Code

Now that your Azure App Service is configured, you can deploy your Django application code.

### Using Local Git Deployment

Local Git deployment allows you to push your code directly from your local Git repository to Azure App Service.

1.  **Enable Local Git Deployment in Azure Portal**:
    *   Navigate to your App Service in the Azure Portal.
    *   In the left-hand menu, under `Deployment`, click on `Deployment Center`.
    *   Select `Local Git` as the source and click `Save`.
    *   Azure will provide you with a Git clone URL and deployment credentials (username and password). Make a note of these.

2.  **Add Azure Git Remote to Your Local Repository**:
    *   Open your terminal or command prompt in your project's root directory.
    *   Add the Azure Git remote using the URL you obtained:
        ```bash
        git remote add azure <Azure_Git_Clone_URL>
        ```
        (e.g., `git remote add azure https://<username>@iia-django-app.scm.azurewebsites.net:443/iia-django-app.git`)

3.  **Push Your Code to Azure**:
    *   Ensure all your changes are committed locally:
        ```bash
        git add .
        git commit -m "Prepare for Azure deployment"
        ```
    *   Push your `main` (or `master`) branch to the `azure` remote:
        ```bash
        git push azure main
        ```
        You will be prompted for the deployment password you noted earlier.

    *   Azure App Service will automatically detect your Python application, install dependencies from `requirements.txt`, and attempt to start your application using the Gunicorn command you configured.

---

## 5. Post-Deployment Steps

After deploying your code, you need to run database migrations and collect static files on the Azure App Service.

### Run Database Migrations

Django migrations apply changes to your database schema. You need to run these on your Azure PostgreSQL database.

1.  **Access the SSH console of your App Service**:
    *   In the Azure Portal, navigate to your App Service.
    *   In the left-hand menu, under `Development Tools`, click on `SSH`.
    *   Click `Go`.
2.  **Navigate to your application directory**:
    *   Once connected via SSH, you'll typically be in `/home`. Your application code is usually in `/home/site/wwwroot/`.
    *   Change directory: `cd /home/site/wwwroot/`
3.  **Run migrations**:
    *   Execute the Django migrate command:
        ```bash
        python manage.py migrate
        ```

### Collect Static Files

Django's `collectstatic` command gathers all static files from your applications into a single directory (`STATIC_ROOT`). WhiteNoise then serves these files.

1.  **Access the SSH console** (if not already connected).
2.  **Navigate to your application directory**: `cd /home/site/wwwroot/`
3.  **Collect static files**:
    *   Execute the Django collectstatic command:
        ```bash
        python manage.py collectstatic
        ```
    *   When prompted to overwrite existing files, type `yes` and press Enter.

## 6. Troubleshooting

Here are some common issues and their solutions:

*   **Application Error / HTTP 500**: Check the App Service logs.
    *   In the Azure Portal, navigate to your App Service.
    *   In the left-hand menu, under `Monitoring`, click on `Log stream`.
    *   Look for Python traceback errors. Common causes include:
        *   Incorrect environment variables (e.g., `SECRET_KEY`, `DATABASE_URL`, API keys).
        *   Database connection issues (firewall, incorrect connection string).
        *   Missing dependencies (ensure all are in `requirements.txt`).
        *   Syntax errors in your code.
*   **Static Files Not Loading**: 
    *   Ensure `collectstatic` was run successfully.
    *   Verify `STATIC_URL` and `STATIC_ROOT` are correct in `settings.py`.
    *   Check if `whitenoise` is correctly configured and in `MIDDLEWARE`.
    *   Ensure `WEBSITES_ENABLE_APP_SERVICE_STORAGE` is set to `False` in App Service settings.
*   **Database Connection Issues**: 
    *   Check PostgreSQL firewall rules to ensure your App Service's outbound IPs are allowed.
    *   Verify the `DATABASE_URL` format and credentials.
    *   Ensure `sslmode=require` is in your `DATABASE_URL`.
*   **Deployment Failed**: 
    *   Check the deployment logs in the `Deployment Center` of your App Service.
    *   Ensure `requirements.txt` is valid and all packages can be installed on Linux.
    *   Check for any syntax errors that might prevent the application from starting.

---

This comprehensive guide should help you successfully deploy your Django application to Azure App Service. Remember to secure your API keys and sensitive information using Azure App Service application settings.