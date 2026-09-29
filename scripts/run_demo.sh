#!/usr/bin/env bash
# ULPF SIH demonstration script.
#
# Requires: bash, curl, jq (optional, for pretty-printing).
# Assumes the backend is running at $BASE (default http://localhost:8000).
#
# This script performs the complete SIH acceptance flow:
#  1. Login as admin
#  2. Ingest CEF log → verify detection, hash, parser, CSE
#  3. Ingest malformed log → verify quarantine
#  4. Ingest unknown format → verify structural analysis
#  5. Verify integrity of first event
#  6. Show dashboard totals
#  7. Show audit trail
#
# This script performs NO attacks. It only exercises the defensive pipeline.

set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
EMAIL="${EMAIL:-admin@ulpf.local}"
PASSWORD="${PASSWORD:-ChangeMe_Admin123!}"

pp() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  else
    cat
  fi
}

step() { echo; echo "==== $1 ===="; }

step "1. Login"
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r .access_token)
echo "Token acquired: ${TOKEN:0:20}…"
AUTH="Authorization: Bearer $TOKEN"

step "2. Ingest CEF log"
CEF='CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|7|rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=administrator dhost=dc01 outcome=failure proto=tcp'
R1=$(curl -s -X POST "$BASE/api/v1/ingest" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"raw\": $(printf '%s' "$CEF" | jq -R .), \"filename\":\"demo.cef\"}")
echo "$R1" | pp
EVID=$(echo "$R1" | jq -r .event_id)

step "3. Ingest malformed log (expect quarantine)"
R2=$(curl -s -X POST "$BASE/api/v1/ingest" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"raw":"CEF:0|broken|header only","filename":"malformed.cef"}')
echo "$R2" | pp

step "4. Ingest unknown vendor log"
UNK='XLOG|2026-01-15T11:20:00Z|203.0.113.55|user=alice|op=read|obj=/etc/passwd|res=denied|sev=warn|hostname=web01'
R3=$(curl -s -X POST "$BASE/api/v1/ingest" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"raw\": $(printf '%s' "$UNK" | jq -R .), \"filename\":\"unknown.log\"}")
echo "$R3" | pp

step "5. Integrity verification of first event"
curl -s "$BASE/api/v1/events/$EVID/integrity" -H "$AUTH" | pp

step "6. Processing timeline of first event"
curl -s "$BASE/api/v1/events/$EVID/timeline" -H "$AUTH" | pp

step "7. Dashboard totals"
curl -s "$BASE/api/v1/dashboard" -H "$AUTH" | jq '.totals'

step "8. Recent audit entries"
curl -s "$BASE/api/v1/audit?size=10" -H "$AUTH" | jq '.items[] | {timestamp, actor, action, resource_id}'

step "Demo complete."
echo "Open $BASE/docs for interactive OpenAPI."
echo "Frontend: http://localhost:5173"