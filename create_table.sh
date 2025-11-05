#!/bin/bash

# Ensure environment variables are set
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_ANON_KEY" ]; then
  echo "Error: SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set."
  exit 1
fi

# Use SUPABASE_JWT if set, otherwise fallback to SUPABASE_ANON_KEY for Authorization header
AUTH_TOKEN="${SUPABASE_JWT:-$SUPABASE_ANON_KEY}"

curl -X POST \
  "${SUPABASE_URL}/rest/v1/rpc" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"fn":"create_conversations_table"}'
