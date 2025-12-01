# Cortex Agents + Threads Streamlit Demo

A Streamlit application that integrates with Snowflake Cortex Agents to provide an interactive chat interface for querying and analyzing data.

## Prerequisites

- Python 3.12 or higher
- [UV](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- A Snowflake account with access to Cortex Agents
- A Snowflake Personal Access Token (PAT)

## Installation

### 1. Install UV (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create and Activate Virtual Environment

Navigate to the project directory and create a virtual environment using UV:

```bash
# Create virtual environment
uv venv

# Activate the environment
source .venv/bin/activate
```

### 3. Install Dependencies

Install all required packages using UV:

```bash
uv sync
```

Or install packages directly:

```bash
uv add streamlit requests sseclient-py
```

## Configuration

### Set up Snowflake Secrets

1. The `.streamlit/secrets.toml` file already exists in your project. Open it for editing:

```bash
# Using your preferred editor
nano .streamlit/secrets.toml
# or
code .streamlit/secrets.toml
```

2. Add your Snowflake credentials to the file:

```toml
account_url = "https://your-account.snowflakecomputing.com"
pat = "your-personal-access-token"
```

**Important:** 
- Replace `your-account` with your actual Snowflake account URL
- Replace `your-personal-access-token` with your Snowflake PAT
- The `account_url` should be the full URL to your Snowflake account (without trailing slash)

### Required Snowflake Setup

This application expects the following Snowflake resources to be configured:
- **Database:** `SNOWFLAKE_INTELLIGENCE`
- **Schema:** `AGENTS`
- **Agent:** `YOUR AGENT NAME`

Make sure these resources exist in your Snowflake account and your PAT has appropriate permissions to access them.

## Running the Application

Once your environment is set up and secrets are configured, start the Streamlit app:

```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Features

- **Interactive Chat Interface:** Ask questions and receive AI-powered responses
- **Thread Management:** Create, view, and manage conversation threads
- **Rich Content Support:** View tables, charts, and annotated responses
- **Persistent Conversations:** All threads are stored and can be accessed later

## Troubleshooting

### Missing Secrets Error
If you see an error about missing secrets, ensure that:
1. The `.streamlit/secrets.toml` file exists
2. Both `account_url` and `pat` fields are populated with valid values
3. There are no extra quotes or spaces in the values

### Connection Issues
If you can't connect to Snowflake:
1. Verify your account URL is correct
2. Ensure your PAT is valid and not expired
3. Check that your Snowflake user has access to the required resources

### Module Not Found Errors
If you encounter import errors:
```bash
# Reinstall dependencies
uv sync --reinstall
```

## Project Structure

```
.
├── .streamlit/
│   └── secrets.toml       # Snowflake credentials (not in version control)
├── streamlit_app.py       # Main application file
├── pyproject.toml         # Project dependencies and metadata
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Development

To modify the application configuration (database, schema, or agent name), edit the `AppConfig` initialization in `streamlit_app.py`:

```python
app = AppConfig(
    database_name="SNOWFLAKE_INTELLIGENCE",
    schema_name="AGENTS",
    agent_name="AGENT_NAME",
    application_name="tech_summit_demo",
)
```

## Security Note

⚠️ **Never commit your `secrets.toml` file to version control!** 

The `.gitignore` file is already configured to exclude this file, but always double-check before committing.

