\# Runbook: High CPU Utilization



\## Incident Indicators

\- CPU usage exceeding 85%

\- Sustained CPU saturation

\- Increased application response times



\## Investigation Steps

1\. Identify high CPU processes using `top`, `htop`, or `ps aux --sort=-%cpu`.

2\. Check whether a single process or multiple processes are consuming CPU.

3\. Review recent deployments, configuration changes, and scheduled jobs.

4\. Inspect application and system logs for repeated errors or restart loops.



\## Remediation Steps

1\. Stop or restart the runaway process if it is safe to do so.

2\. Restart the affected application service if CPU usage does not recover.

3\. Disable or reschedule resource-intensive background jobs.

4\. Scale application resources if high CPU demand is legitimate.



\## Escalation Criteria

Escalate to the Infrastructure or Application Team if CPU usage remains above 95% after remediation or the service becomes unavailable.

