\# Runbook: Service Outage



\## Incident Indicators

\- Service status is DOWN or FAILED

\- HTTP endpoint returns 500, 502, or 503

\- Health checks are failing



\## Investigation Steps

1\. Check the service status using `systemctl status <service>`.

2\. Inspect recent application and system logs.

3\. Verify network connectivity and dependent services.

4\. Check CPU, memory, and disk resource availability.



\## Remediation Steps

1\. Restart the affected service using `systemctl restart <service>`.

2\. Verify the service is active after restart.

3\. Re-run the health check endpoint.

4\. Roll back the most recent deployment if the outage began after a release.



\## Escalation Criteria

Escalate to the On-Call Infrastructure or Application Team if the service does not recover after restart or multiple services are affected.

