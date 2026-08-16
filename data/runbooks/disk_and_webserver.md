# Runbook: Disk Utilization & Web Server Outages

## Incident Indicators
- Disk usage exceeding 90%
- Apache / Nginx status reported as DOWN or HTTP status 502/503

## Root Cause
High disk usage prevents web servers from creating lock files, socket connections, or writing access/error logs, resulting in process crash or failure to start.

## Remediation Steps
1. Inspect log directories (`/var/log`) for oversized log files.
2. Clear temporary files in `/tmp` and rotate active logs using `logrotate`.
3. Verify disk space using `df -h`.
4. Once disk usage drops below 90%, restart the web server service (`systemctl restart apache2` or `systemctl restart nginx`).

## Escalation Criteria
Escalate to Infrastructure/Storage Team if disk usage remains >95% after log cleanup or if unpartitioned disk space is exhausted.