#!/usr/bin/env python3
"""OpsGuard Self-Healing Demonstration Script.

Demonstrates the complete incident lifecycle:
1. Service registration
2. Failure simulation
3. Detection
4. Incident creation
5. Evidence collection
6. Diagnosis
7. Remediation recommendation
8. Approval
9. Execution
10. Recovery verification
11. Resolution
"""

import time
import uuid

import httpx

BASE_URL = "http://localhost:8000"


def print_step(step_num: int, message: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Step {step_num}: {message}")
    print(f"{'='*60}")


def main() -> None:
    print("\n" + "=" * 60)
    print("  OpsGuard Self-Healing Demonstration")
    print("  Scenario: Bad Deployment")
    print("=" * 60)

    with httpx.Client(timeout=30.0) as client:
        # Step 1: Authenticate
        print_step(1, "Authenticate")
        resp = client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "admin", "password": "admin"},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  Authenticated successfully")

        # Step 2: Register a service
        print_step(2, "Register Service (simulating healthy deployment)")
        service_name = f"demo-api-{uuid.uuid4().hex[:6]}"
        resp = client.post(
            f"{BASE_URL}/api/v1/services",
            headers=headers,
            json={
                "name": service_name,
                "url": f"{BASE_URL}/health",
                "kind": "application",
                "environment": "demonstration",
            },
        )
        resp.raise_for_status()
        service_id = resp.json()["id"]
        print(f"  Service registered: {service_name} (ID: {service_id})")

        # Step 3: Verify service is healthy
        print_step(3, "Verify Service Health")
        resp = client.get(
            f"{BASE_URL}/api/v1/services/{service_id}/health",
            headers=headers,
        )
        health = resp.json()
        print(f"  Availability: {health['availability_pct']}%")
        print(f"  Status: {health['service']['health_status']}")

        # Step 4: Trigger failure simulation
        print_step(4, "Deploy Bad Version (simulate failure)")
        resp = client.post(
            f"{BASE_URL}/api/v1/simulator/trigger",
            headers={**headers, "Content-Type": "application/json"},
            json={
                "simulation_type": "http_500",
                "duration_seconds": 90,
                "target_service": service_name,
            },
        )
        sim_result = resp.json()
        print(f"  Failure simulation started: {sim_result['simulation_id']}")

        # Step 5: Wait for detection
        print_step(5, "Wait for Detection Engine (20 seconds)")
        time.sleep(20)

        # Step 6: Check for auto-created incidents
        print_step(6, "Check for Auto-Created Incidents")
        resp = client.get(f"{BASE_URL}/api/v1/incidents", headers=headers)
        incidents = resp.json()

        if not incidents:
            print("  No incidents yet — waiting 15 more seconds...")
            time.sleep(15)
            resp = client.get(f"{BASE_URL}/api/v1/incidents", headers=headers)
            incidents = resp.json()

        if not incidents:
            print("  No incidents created via scheduler.")
            print("  Creating incident directly to demonstrate full workflow...")
            resp = client.post(
                f"{BASE_URL}/api/v1/incidents",
                headers=headers,
                json={
                    "title": "High CPU Usage — Simulated Bad Deployment",
                    "severity": "HIGH",
                    "source": "prometheus",
                    "description": "CPU usage exceeded threshold: 95% (threshold: 85%)",
                    "symptoms": "High CPU utilization: 95.0% (confidence=0.99)",
                },
            )
            resp.raise_for_status()
            incident = resp.json()
            incident_id = incident["id"]
            print(f"  Incident created: {incident['incident_key']}")
        else:
            incident = incidents[0]
            incident_id = incident["id"]
            print(f"  Incident auto-created: {incident['incident_key']}")
            print(f"  Title: {incident['title']}")
            print(f"  Severity: {incident['severity']}")
            print(f"  Status: {incident['status']}")

        # Step 7: Trigger investigation (evidence + diagnosis + remediation)
        print_step(7, "Trigger Investigation (Evidence + Diagnosis + Remediation)")
        resp = client.post(
            f"{BASE_URL}/api/v1/incidents/{incident_id}/investigate",
            headers=headers,
        )
        resp.raise_for_status()
        incident = resp.json()
        print(f"  Investigation triggered")
        print(f"  Status: {incident['status']}")

        # Wait for investigation to complete
        time.sleep(3)

        # Step 8: View incident timeline
        print_step(8, "View Incident Timeline")
        resp = client.get(
            f"{BASE_URL}/api/v1/incidents/{incident_id}/timeline",
            headers=headers,
        )
        timeline = resp.json()

        events = timeline.get("events", [])
        print(f"  Timeline events: {len(events)}")
        for event in events[:10]:
            msg = event["message"][:70]
            print(f"    [{event['event_type']}] {msg}")

        # Step 9: View evidence
        print_step(9, "View Collected Evidence")
        evidence = timeline.get("evidence", [])
        print(f"  Evidence items collected: {len(evidence)}")
        for ev in evidence:
            print(f"    - {ev['evidence_type']} (from {ev['source']})")

        # Step 10: View diagnosis
        print_step(10, "View Diagnosis")
        diagnoses = timeline.get("diagnoses", [])
        if diagnoses:
            for i, d in enumerate(diagnoses, 1):
                print(f"  Diagnosis #{i}:")
                print(f"    Probable cause: {d['probable_cause'][:80]}")
                print(f"    Confidence: {d['confidence']*100:.0f}%")
                if d.get("recommended_action"):
                    print(f"    Recommended action: {d['recommended_action']}")
        else:
            print("  No diagnosis available")

        # Step 11: Request remediation
        print_step(11, "Request Remediation (restart_service)")
        resp = client.post(
            f"{BASE_URL}/api/v1/remediation/incidents/{incident_id}/actions",
            headers=headers,
            json={"action_type": "restart_service"},
        )
        resp.raise_for_status()
        action = resp.json()
        action_id = action["id"]
        print(f"  Action requested: {action['action_type']}")
        print(f"  Risk level: {action['risk_level']}")
        print(f"  Approval required: {action['approval_required']}")
        print(f"  Status: {action['status']}")

        # Step 12: Approve remediation
        print_step(12, "Approve Remediation (human-in-the-loop)")
        resp = client.post(
            f"{BASE_URL}/api/v1/remediation/actions/{action_id}/approve",
            headers=headers,
            json={"approved": True, "notes": "Approved via demonstration"},
        )
        resp.raise_for_status()
        approved = resp.json()
        print(f"  Approved by: {approved['approved_by']}")
        print(f"  Status: {approved['status']}")

        # Step 13: Execute remediation
        print_step(13, "Execute Remediation")
        resp = client.post(
            f"{BASE_URL}/api/v1/remediation/actions/{action_id}/execute",
            headers=headers,
        )
        resp.raise_for_status()
        executed = resp.json()
        print(f"  Execution result: {executed['result']}")
        print(f"  Status: {executed['status']}")
        if executed.get("output"):
            print(f"  Output: {executed['output'][:100]}")

        # Step 14: Wait for verification
        print_step(14, "Wait for Recovery Verification (10 seconds)")
        time.sleep(10)

        # Step 15: Check final status
        print_step(15, "Check Final Incident Status")
        resp = client.get(
            f"{BASE_URL}/api/v1/incidents/{incident_id}",
            headers=headers,
        )
        final = resp.json()
        print(f"  Final status: {final['status']}")
        print(f"  Remediation status: {final.get('remediation_status', 'N/A')}")
        print(f"  Duration: {final.get('duration', 'N/A')} seconds")
        if final.get("probable_root_cause"):
            print(f"  Root cause: {final['probable_root_cause'][:80]}")

        # Step 16: View audit trail
        print_step(16, "View Audit Trail")
        resp = client.get(
            f"{BASE_URL}/api/v1/audit?incident_id={incident_id}",
            headers=headers,
        )
        audit = resp.json()
        print(f"  Audit entries: {len(audit)}")
        for entry in audit[:10]:
            performer = entry.get("performed_by", "system")
            print(f"    - {entry['action']} (by {performer})")

        # Summary
        print("\n" + "=" * 60)
        print("  DEMONSTRATION SUMMARY")
        print("=" * 60)
        print(f"  Incident: {final['incident_key']} — {final['title'][:50]}")
        print(f"  Severity: {final['severity']}")
        print(f"  Final Status: {final['status']}")
        print(f"  Remediation: {final.get('remediation_status', 'N/A')}")
        print(f"  Evidence Items: {len(evidence)}")
        print(f"  Diagnoses: {len(diagnoses)}")
        print(f"  Audit Trail: {len(audit)} entries")

        if final["status"] == "RESOLVED":
            print("\n  SUCCESS! Incident was automatically resolved.")
        else:
            print(f"\n  Incident status: {final['status']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
