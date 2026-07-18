# Data Protection (GDPR principles + Tunisian INPDP)

SentinelleRx is a supply-chain platform, not a clinical record system. It is
designed to hold **no patient health records and no prescriptions tied to
identifiable individuals**.

## Data minimization
- The platform stores stock, sales *counts*, forecasts, and supply-chain events —
  aggregate quantities, never patient-level dispensing records.
- Citizen search is **anonymous** (no login, no stored query-to-person link).
- Reservations store only a **hashed** contact (`citizen_contact_hash`,
  SHA-256), never a raw phone/email, and expire automatically.

## Lawful basis & roles
- Professional users (PCT, authorities, pharmacists, suppliers) authenticate via
  Keycloak; their identities are managed in the realm, not duplicated with
  credentials in the app DB (`users` stores only the Keycloak subject + role +
  org link).

## Security of processing
- Encryption in transit (TLS) and at rest (DB/S3 provider-level).
- RBAC + MFA for privileged roles; append-only audit trail of every mutation.

## Retention
| Data | Retention |
|---|---|
| Transactional (stock/sales) | Rolling operational window + archival for model training |
| Predictions / explanations | Refreshed each scoring run; historical kept for evaluation |
| Reservations (hashed) | Until expiry + short grace, then purged |
| Audit logs | Retained per regulatory requirement (e.g. 12 months+) |

## Data subject rights
- Because citizen usage is anonymous, there is typically no personal data to
  export or erase. Where a hashed reservation exists, it is unlinkable to an
  identity and self-expires.
- Professional user data is administered in Keycloak (access, rectification,
  deletion handled at the IdP).

## DPIA note
A Data Protection Impact Assessment should accompany national rollout, covering
the external-data connectors (epidemiological signals) and confirming that no
re-identification is possible from aggregate stock/sales data.
