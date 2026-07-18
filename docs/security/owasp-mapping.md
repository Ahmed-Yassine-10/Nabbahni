# OWASP Top 10 (2021) — Control Mapping

How SentinelleRx addresses each category. Items marked *(later pass)* are
designed but not fully implemented in pass 1.

| # | Risk | Controls in SentinelleRx |
|---|---|---|
| A01 | Broken Access Control | Keycloak RBAC with 6 realm roles; `require_roles()` dependency on every protected route; regional/pharmacy scoping in `alerts`/`stock`; server-side checks (never client-trusted). |
| A02 | Cryptographic Failures | TLS in transit (Ingress + cert-manager); RS256 JWT validation against realm JWKS; secrets via ExternalSecrets, never in code; DB/S3 encryption at rest *(infra-provided)*. |
| A03 | Injection | SQLAlchemy parameterized queries throughout; Pydantic v2 validation on all inputs; no string-built SQL; PostGIS via typed functions. |
| A04 | Insecure Design | Human-in-the-loop for all decisions; explainability required; append-only audit log; least-privilege roles; threat-modeled data flows. |
| A05 | Security Misconfiguration | Non-root containers; minimal images; healthchecks; CORS allow-list; brute-force protection + password policy in Keycloak realm; default-deny NetworkPolicy. |
| A06 | Vulnerable Components | `security-scan` workflow: Trivy (fs + image), `pip-audit`, `npm audit`; pinned dependencies. |
| A07 | Identification & Auth Failures | Keycloak: MFA (OTP) required for `pct_admin` & `regional_authority`; account lockout; short access-token lifetime (15 min); PKCE for the web client. |
| A08 | Software & Data Integrity | Signed container images *(cosign — later pass)*; MLflow model provenance; migrations reviewed; CI gates. |
| A09 | Logging & Monitoring Failures | Append-only `audit_logs` on all mutations; Prometheus + Grafana + Alertmanager; OpenTelemetry traces; Sentry error capture. |
| A10 | SSRF | No user-controlled outbound fetches in the request path; external connectors are allow-listed and run in ETL workers, not the API. |
