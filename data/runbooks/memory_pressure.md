# Memory Pressure

## Symptoms
- Memory utilization exceeds 85%
- OOMKilled events in Kubernetes
- Application crashes or restarts

## Evidence to Collect
- Current memory usage
- Memory usage trend
- OOMKilled events
- Recent deployments

## Diagnosis
1. Check for memory leaks
2. Verify memory limits are appropriate
3. Check if memory spike correlates with deployment
4. Identify memory-intensive processes

## Safe Actions
- Check memory usage trends
- Review application logs for OOM events
- Verify memory limits

## Risky Actions
- Restart the service (MEDIUM risk)
- Increase memory limits (MEDIUM risk)

## Rollback Instructions
- If restart fails, rollback to previous deployment
- Revert memory limit changes

## Verification Steps
- Memory usage drops below 85%
- No new OOMKilled events
- Application remains stable
