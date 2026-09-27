# Service Outage

## Symptoms
- Service unreachable
- Health check failures
- Connection timeouts

## Evidence to Collect
- Health check results
- Service logs
- Recent deployments
- Dependency status

## Diagnosis
1. Check if service process is running
2. Verify network connectivity
3. Check dependency services
4. Review recent deployments

## Safe Actions
- Check service status
- Review logs
- Verify dependencies

## Risky Actions
- Restart the service (MEDIUM risk)
- Rollback deployment (HIGH risk)

## Rollback Instructions
- `kubectl rollout undo deployment/<name> -n <namespace>`

## Verification Steps
- Health check returns 200
- Service responds to requests
- No new errors in logs
