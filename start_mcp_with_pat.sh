#!/bin/bash

# Supabase PAT를 입력받아 MCP 서버 시작
echo "Supabase PAT를 입력하세요: "
read -r PAT

# MCP 서버 시작 (PAT와 함께)
npx -y @supabase/mcp-server-supabase@latest \
  --project-ref yzzktqetfyaarhakvgfk \
  --access-token $PAT
