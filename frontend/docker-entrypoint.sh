#!/bin/sh

# Default to empty string if not set, or a specific fallback
: "${ai_customer_support_ai_agent_service_SERVICE_ENDPOINT:=http://localhost:8000}"

# Replace the placeholder in index.html with the actual URL from environment variable
# We use sed to replace 'BACKEND_API_URL_PLACEHOLDER' with the value of the env var
sed -i "s|BACKEND_API_URL_PLACEHOLDER|${ai_customer_support_ai_agent_service_SERVICE_ENDPOINT}|g" /usr/share/nginx/html/index.html

# Execute the CMD (start nginx)
exec "$@"
