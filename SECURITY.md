
# Security

- Secrets via `.env` and environment vars. Do not commit secrets.
- TLS in transit (handled by hosting/proxy in production).
- PII minimization; encrypt sensitive data at rest when persisted.
- Role-based access to logs and data.
- Regular dependency scanning.
