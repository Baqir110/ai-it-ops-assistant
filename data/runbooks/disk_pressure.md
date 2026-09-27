# Disk Pressure

## Symptoms
- Disk utilization exceeds 90%
- Log files growing rapidly
- Potential service failure

## Evidence to Collect
- Disk usage by directory
- Large files
- Log rotation configuration

## Diagnosis
1. Identify large files
2. Check log rotation
3. Review temporary files
4. Verify disk capacity

## Safe Actions
- Check disk usage
- Review large files
- Verify log rotation

## Risky Actions
- Clear old logs (LOW risk)
- Increase disk space (MEDIUM risk)

## Rollback Instructions
- If cleanup causes issues, restore from backup
- If disk increase fails, revert to previous size

## Verification Steps
- Disk usage drops below 90%
- Services continue to run
- Logs are being written
