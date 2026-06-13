# Federal Cross-Check Policy (State ↔ Federal Federation)

Programs with federal funding require an identity and income cross-check against
the federal data authority (Tier 1). The state portal does not hold federal
records directly; it requests them through the identity federation broker, which
issues a scoped access token for the federal data path.

Access is governed by assurance level. Routine state operations run at standard
assurance; reaching federal records requires a high-assurance token issued only
to authorized service identities. The federation policy checkpoint validates the
token before any federal record is returned.

Residents cannot query federal records themselves. Only the portal's federal
cross-check function, acting under its service identity, may do so — and only for
the specific record tied to an open determination.

This federation path is part of the state's ongoing migration to a zero-trust
architecture. During migration, legacy internal services continue to operate
under implicit network trust while the federal path is brought under explicit,
per-request verification.
