"""Environment variable configuration for AwsRouter.

The ``scripts/secrets/sync_env_vars_to_lambda.py`` script reads
``REQUIRED_ENV_VARS`` to determine which keys to pull from the root ``.env``
and push to AWS Lambda. Add a key here AND set it in ``.env`` to surface it
on the function.
"""

REQUIRED_ENV_VARS = [
    # Powertools — controls service name in traces/logs and log verbosity.
    "POWERTOOLS_SERVICE_NAME",
    "POWERTOOLS_LOG_LEVEL",
]
