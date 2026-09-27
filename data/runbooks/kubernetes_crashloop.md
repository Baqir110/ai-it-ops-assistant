# Kubernetes CrashLoopBackOff

## Symptoms
- Pod in CrashLoopBackOff state
- Repeated container restarts
- Service unavailable

## Evidence to Collect
- Pod status and events
- Container logs
- Resource limits
- Recent deployments

## Diagnosis
1. Check pod events: `kubectl describe pod <name>`
2. Review container logs
3. Check for OOMKilled
4. Verify ConfigMaps and Secrets exist

## Safe Actions
- Check pod events
- Review logs
- Verify configuration

## Risky Actions
- Rollout restart (MEDIUM risk)
- Rollback deployment (HIGH risk)

## Rollback Instructions
- `kubectl rollout undo deployment/<name> -n <namespace>`

## Verification Steps
- Pod reaches Running state
- Container restart count stabilizes
- Service health checks pass
