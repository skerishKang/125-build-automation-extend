curl -X POST \
  "https://yzzktqetfyaarhakvgfk.supabase.co/rest/v1/rpc" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl6emt0cWV0ZnlhYXJoYWt2Z2ZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyMzk3MTMsImV4cCI6MjA3NzgxNTcxM30.9j9AEW1l2g3B1PFa_qV5hj1ESIuVTZ0GnwBBanhv8-s" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl6emt0cWV0ZnlhYXJoYWt2Z2ZrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyMzk3MTMsImV4cCI6MjA3NzgxNTcxM30.9j9AEW1l2g3B1PFa_qV5hj1ESIuVTZ0GnwBBanhv8-s" \
  -H "Content-Type: application/json" \
  -d '{"fn":"create_conversations_table"}'
