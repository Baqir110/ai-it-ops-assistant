# Certificate Expiry

## Symptoms
- SSL certificate expiring within 14 days
- Browser warnings for users
- Potential service outage

## Evidence to Collect
- Certificate expiry date
- Certificate issuer
- Domain configuration

## Diagnosis
1. Check certificate expiry date
2. Verify auto-renewal configuration
3. Check certificate authority

## Safe Actions
- Review certificate details
- Check auto-renewal setup

## Risky Actions
- Renew certificate (MEDIUM risk — requires approval)

## Rollback Instructions
- If renewal fails, restore previous certificate
- Verify certificate chain

## Verification Steps
- New certificate is valid
- No browser warnings
- HTTPS connections succeed
