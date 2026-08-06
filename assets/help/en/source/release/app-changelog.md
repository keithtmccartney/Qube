# What's new in Qube 1.3.0

## Common questions

- What's new in Qube?
- What changed in the latest Qube update?
- Where do I see version history?

Offline Pro license verification in shipped builds, plus maintainer tooling for signing keys and batch license issuance.

## Highlights

### Production license signing

Shipped builds embed the production signing key so Pro licenses verify fully offline.
- Import Pro licenses without contacting a server on first verify
- Production `.qube-license` files validate against the embedded production key

### Signing key generator

Maintainers can generate Ed25519 signing keys and register public keys for pack verification.

### Batch license issuance

Issue multiple customer licenses in one run with a CSV manifest and per-customer key files.

### Licensing CLI bootstrap

Licensing maintainer scripts bootstrap the repo root when run directly.

## Where to find it

Open **Settings → About → Version history** for the full searchable changelog.

## Also called

app release notes, version history, what's new in qube, qube changelog
