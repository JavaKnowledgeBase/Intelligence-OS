# Security Policy

Developer: Ravi Kafley

This project follows an OWASP-aligned secure development baseline.

## Baseline

- OWASP ASVS as the primary application security verification standard
- OWASP SAMM for development process maturity
- OWASP Top 10 for common web application risk coverage
- OWASP Cheat Sheet Series for implementation guidance

## Current Project Rules

- No secrets in source control
- No plaintext credentials beyond temporary local-only demo placeholders
- Explicit input validation on API request models
- Least-privilege CORS and allowlists by environment
- Security headers enabled on HTTP responses
- Authentication and authorization changes must be reviewed for abuse cases
- Dependency updates should be checked for known vulnerabilities
- Logging must avoid passwords, tokens, and sensitive personal data

## Vulnerability Reporting

Please report security concerns privately to the project owner before public disclosure.

## Current Gap Areas

- Demo authentication must be replaced with production JWT/session handling before deployment
- Rate limiting and lockout controls should be added before internet exposure
- CSRF strategy must be defined if cookie-based auth is introduced
- Database, object storage, and vector store access controls must be enforced per environment

