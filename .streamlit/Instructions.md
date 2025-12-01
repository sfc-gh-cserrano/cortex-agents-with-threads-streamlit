# Secrets File

Create a new secrets.toml file and add the following keys:
- account_url = "https://YOUR-ACCOUNT.snowflakecomputing.com"
- pat = "YOUR PERSONAL ACCESS TOKEN"

> You can create a PAT in Snowsight by navigating to your user settings or programatically using :
``` sql
ALTER USER [ IF EXISTS ] [ <username> ] ADD { PROGRAMMATIC ACCESS TOKEN | PAT } <token_name>
  [ ROLE_RESTRICTION = '<string_literal>' ]
  [ DAYS_TO_EXPIRY = <integer> ]
  [ MINS_TO_BYPASS_NETWORK_POLICY_REQUIREMENT = <integer> ]
  [ COMMENT = '<string_literal>' ]
  ```
  More info: [Here](https://docs.snowflake.com/en/sql-reference/sql/alter-user-add-programmatic-access-token)
