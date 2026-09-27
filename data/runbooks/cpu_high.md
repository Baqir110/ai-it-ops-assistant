# CPU High

## Symptoms
- CPU utilization exceeds 85%
- Application response times degraded
- Possible service unresponsiveness

## Evidence to Collect
- Current CPU usage per core
- Top CPU-consuming processes
- Recent deployments
- Recent configuration changes

## Diagnosis
1. Check if CPU spike correlates with a recent deployment
2. Identify top CPU-consuming processes
3. Check for runaway processes or infinite loops
4. Verify if traffic increase justifies CPU usage

## Safe Actions
- Identify high CPU processes
- Check application logs for errors
- Verify recent deployments

## Risky Actions
- Restart the service (MEDIUM risk)
- Scale up the deployment (MEDIUM risk)

## Rollback Instructions
- If restart fails, rollback to previous deployment version
- Use `kubectl rollout undo deployment/<name>`

## Verification Steps
- CPU usage drops below 85%
- Application response times return to normal
- No new errors in logs
