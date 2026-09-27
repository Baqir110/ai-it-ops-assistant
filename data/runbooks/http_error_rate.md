# HTTP Error Rate Spike

## Symptoms
- HTTP 5xx error rate exceeds 5%
- User-facing errors
- Elevated error rates in monitoring

## Evidence to Collect
- Error rate metrics
- Error response codes
- Recent deployments
- Application logs

## Diagnosis
1. Check if error spike correlates with deployment
2. Identify which endpoints are failing
3. Check downstream dependencies
4. Review application logs for exceptions

## Safe Actions
- Identify failing endpoints
- Check error logs
- Verify downstream services

## Risky Actions
- Rollback deployment (HIGH risk)
- Restart service (MEDIUM risk)

## Rollback Instructions
- `kubectl rollout undo deployment/<name> -n <namespace>`

## Verification Steps
- Error rate drops below 1%
- No new 5xx errors
- User requests succeed
