# =============================================================================
# Samba AD DC — DOCUMENTED FALLBACK for the legacy trust core (§2.7).
#
# The protocol's PREFERRED AD node is a genuine Windows Server 2022 DC on a Vultr
# host, because authentic Microsoft AD makes the Kerberos/DCSync findings
# credible rather than emulator-dependent (§2.6). This Samba container is the
# timeboxed cut to take WITHOUT HESITATION if real Windows AD + cross-provider
# Tailscale meshing isn't stable in the Week 2 build window — recorded as a
# documented limitation, never allowed to threaten the primary contribution.
#
# Provisions a realistic domain: a kerberoastable service account with an SPN
# (T1558) and a DCSync-capable privileged account (T1003.006 / T1110).
# =============================================================================
FROM debian:12-slim
ENV DEBIAN_FRONTEND=noninteractive
# AD DC provisioning on Debian 12 needs the directory-services DB modules and
# common-bin (these carry the schema setup support `samba-tool domain provision`
# requires; the main `samba` package alone is not enough).
RUN apt-get update && apt-get install -y --no-install-recommends \
        samba samba-common-bin samba-dsdb-modules samba-vfs-modules \
        smbclient winbind krb5-user ldb-tools ldap-utils dnsutils \
    && rm -rf /var/lib/apt/lists/*
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# DNS, Kerberos, LDAP, SMB, Global Catalog
EXPOSE 53/tcp 53/udp 88/tcp 88/udp 135/tcp 389/tcp 389/udp 445/tcp 464/tcp 464/udp 636/tcp 3268/tcp 3269/tcp
ENTRYPOINT ["/entrypoint.sh"]
