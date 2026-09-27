# Deployment Rollback

## Symptoms
- Error rate spike after deployment
- Service degradation after release
- User-reported issues

## Evidence to Collect
- Deployment timestamp
- Error rate before and after
- Deployment logs
- Application logs

## Diagnosis
1. Confirm correlation between deployment and errors
2. Identify the deployment version
3. Check if rollback is needed
4. Verify previous version was stable

## Safe Actions
- Confirm deployment correlation
- Prepare rollback plan
- Notify stakeholders

## Risky Actions
- Execute rollback (HIGH risk — requires approval)

## Rollback Instructions
1. `kubectl rollout undo deployment/<name> -n <namespace>`
2. Verify rollback: `kubectl rollout status deployment/<name>`
3. Monitor error rates

## Verification Steps
- Error rate returns to baseline
- Service health checks pass
- No new errors in logs
