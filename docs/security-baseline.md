# OWASP Security Baseline

Developer: Ravi Kafley

This repository should be developed against an OWASP-aligned baseline rather than ad hoc security decisions.

## Primary References

- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP SAMM: https://owasp.org/www-project-samm/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/

## Target

Aim for OWASP ASVS Level 2 as the default baseline for this platform because it handles business-sensitive workflows, authentication, and investor-facing data.

## What This Means For Torilaure

### Architecture

- Keep trust boundaries explicit between frontend, API, workers, storage, and external providers
- Use deny-by-default authorization decisions
- Separate local demo shortcuts from production code paths

### Authentication

- Store passwords only as strong salted hashes
- Use secure token/session issuance and expiration
- Add rate limiting, lockout, and brute-force protections
- Enforce MFA for privileged users in production

### Session Management

- Expire sessions predictably
- Rotate tokens or sessions after privilege changes
- Never expose secrets in browser storage for production deployments

### Access Control

- Enforce server-side authorization on every protected route and object
- Use tenant-aware checks for project, document, and report access
- Test for horizontal and vertical privilege escalation

### Input and Output Handling

- Validate all inputs with typed schemas
- Encode output based on rendering context
- Reject unsafe file types and scan uploads before processing

### Cryptography

- Use vetted libraries and platform primitives only
- Protect secrets with environment-specific secret management
- Never invent custom cryptographic schemes

### Logging and Monitoring

- Log authentication events, access decisions, and security-relevant failures
- Exclude passwords, tokens, and sensitive business data from logs
- Add alerting for suspicious login and privilege activity

### Dependency and Supply Chain

- Run dependency audit checks regularly
- Pin critical runtime dependencies
- Review transitive dependencies for security relevance

### Secure Delivery

- Require code review for auth, storage, and externally reachable surfaces
- Run static analysis, linting, dependency checks, and security tests in CI
- Track high-risk findings to remediation before release

## Immediate Controls Already Added

- Explicit CORS origin allowlist
- Security headers middleware
- Hashed demo-password verification instead of plaintext comparison
- Protected frontend routes for authenticated areas

## Immediate Next Controls

1. Replace demo auth with real JWT/session issuance and server-side token validation.
2. Add backend rate limiting for auth and high-risk endpoints.
3. Add structured audit logging for login, logout, project access, and admin actions.
4. Add dependency audit commands to CI for Node and Python.
5. Add authorization checks per project/resource before multi-tenant data is introduced.

