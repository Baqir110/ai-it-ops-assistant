\# Runbook: High Memory Utilization



\## Incident Indicators

\- RAM usage exceeding 85%

\- Memory usage continuously increasing

\- Out-of-memory errors

\- Application crashes or slow response times



\## Investigation Steps

1\. Identify memory-intensive processes using `top`, `htop`, or `ps aux --sort=-%mem`.

2\. Check system logs for out-of-memory killer events.

3\. Review application logs for memory leaks.

4\. Check swap usage and available memory.



\## Remediation Steps

1\. Restart the process with abnormal memory consumption if safe.

2\. Restart the affected application service.

3\. Investigate potential memory leaks.

4\. Increase available memory or scale the workload if required.



\## Escalation Criteria

Escalate to the Application or Infrastructure Team if memory usage remains above 95%, the system triggers OOM events, or services repeatedly crash.

