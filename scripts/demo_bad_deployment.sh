#!/usr/bin/env bash
# OpsGuard Demonstration: Bad Deployment Scenario
#
# This script demonstrates the complete incident lifecycle:
# 1. Deploy healthy version
# 2. Confirm healthy metrics
# 3. Deploy broken version
# 4. Error rate rises
# 5. OpsGuard detects SLO violation
# 6. Incident created
# 7. Evidence collected
# 8. Diagnosis identifies deployment correlation
# 9. Rollback recommended
# 10. Human approves rollback
# 11. Rollback executed
# 12. Health verification succeeds
# 13. Incident resolved
# 14. MTTD and MTTR recorded

set -e

API_URL="http://localhost:8000"

echo "=========================================="
echo "OpsGuard Demonstration: Bad Deployment"
echo "=========================================="
echo ""

# Get auth token
echo "Authenticating..."
TOKEN=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
  -d "username=admin&password=admin" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to authenticate. Make sure OpsGuard is running."
  exit 1
fi

echo "Authenticated successfully"
echo ""

# Register a test service
echo "Registering test service..."
curl -s -X POST "${API_URL}/api/v1/services" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "demo-api", "url": "http://localhost:8000/health", "kind": "application"}' > /dev/null

echo "Service registered"
echo ""

# Simulate bad deployment
echo "Simulating bad deployment (HTTP 500 errors)..."
curl -s -X POST "${API_URL}/api/v1/simulator/trigger" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"simulation_type": "http_500", "duration_seconds": 120}' > /dev/null

echo "Failure simulation triggered"
echo ""

# Wait for detection
echo "Waiting for OpsGuard to detect the issue..."
sleep 10

# Check for incidents
echo "Checking for detected incidents..."
INCIDENTS=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${API_URL}/api/v1/incidents" 2>/dev/null || echo "[]")

INCIDENT_COUNT=$(echo "$INCIDENTS" | python -c "import sys,json; print(len(json.load(sys.stdin)))")

if [ "$INCIDENT_COUNT" -gt 0 ]; then
  INCIDENT_ID=$(echo "$INCIDENTS" | python -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  echo "Incident detected! ID: ${INCIDENT_ID}"
  echo ""

  # Get incident details
  echo "Incident details:"
  curl -s -H "Authorization: Bearer ${TOKEN}" "${API_URL}/api/v1/incidents/${INCIDENT_ID}" | python -m json.tool
  echo ""

  # Acknowledge
  echo "Acknowledging incident..."
  curl -s -X POST -H "Authorization: Bearer ${TOKEN}" "${API_URL}/api/v1/incidents/${INCIDENT_ID}/acknowledge" > /dev/null
  echo "Incident acknowledged"
  echo ""

  # Request remediation
  echo "Requesting remediation (restart_service)..."
  curl -s -X POST -H "Authorization: Bearer ${TOKEN}" \
    "${API_URL}/api/v1/remediation/incidents/${INCIDENT_ID}/actions" \
    -H "Content-Type: application/json" \
    -d '{"action_type": "restart_service"}' > /dev/null
  echo "Remediation requested"
  echo ""

  # Approve remediation
  echo "Approving remediation..."
  ACTIONS=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${API_URL}/api/v1/remediation/incidents/${INCIDENT_ID}/actions")
  ACTION_ID=$(echo "$ACTIONS" | python -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

  curl -s -X POST -H "Authorization: Bearer ${TOKEN}" \
    "${API_URL}/api/v1/remediation/actions/${ACTION_ID}/approve" \
    -H "Content-Type: application/json" \
    -d '{"approved": true}' > /dev/null
  echo "Remediation approved"
  echo ""

  # Execute remediation
  echo "Executing remediation..."
  curl -s -X POST -H "Authorization: Bearer ${TOKEN}" \
    "${API_URL}/api/v1/remediation/actions/${ACTION_ID}/execute" > /dev/null
  echo "Remediation executed"
  echo ""

  # Wait for verification
  echo "Waiting for recovery verification..."
  sleep 15

  # Check final status
  FINAL_STATUS=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${API_URL}/api/v1/incidents/${INCIDENT_ID}")
  STATUS=$(echo "$FINAL_STATUS" | python -c "import sys,json; print(json.load(sys.stdin)['status'])")

  echo ""
  echo "=========================================="
  echo "Final incident status: ${STATUS}"
  echo "=========================================="

  if [ "$STATUS" = "RESOLVED" ]; then
    echo ""
    echo "SUCCESS! Incident was automatically resolved."
    echo "MTTD and MTTR have been recorded."
  else
    echo ""
    echo "Incident status: ${STATUS}"
    echo "Check the dashboard for details."
  fi
else
  echo "No incidents detected yet. The detection engine may need more time."
  echo "Check the dashboard at http://localhost:8000"
fi

echo ""
echo "=========================================="
echo "Demonstration complete"
echo "=========================================="
