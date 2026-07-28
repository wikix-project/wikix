# Privacy

Wikix is local-first software. It has no Wikix-operated server, analytics, telemetry, shared
credentials, or account database.

## Data flows

Wikix sends requests directly from your computer to X's official OAuth and API endpoints. The
requested data is written to the collection directory you select. Rich and folder data is fetched
only when you opt in with `--rich` or `--folders`.

Access and refresh tokens are stored in Keychain, Secret Service/KWallet, or Windows Credential
Locker through the Python keyring interface. Headless users may inject tokens through
`WIKIX_ACCESS_TOKEN` and `WIKIX_REFRESH_TOKEN`; Wikix does not write injected values to disk or to
the credential store.

Raw API pages exist only in the collection's staging area while a snapshot is incomplete. They are
deleted after a successful reconciliation. Persistent state retains hashes, counts, timestamps,
account/profile metadata, and recovery information—not removed post bodies.

## Your responsibilities

Markdown and JSONL files may contain private or sensitive posts, usernames, URLs, and annotations.
Choose an appropriate storage location, backup policy, sync provider, and access control. Anyone
with filesystem access may be able to read the export.

Wikix cannot control data handling by X, your operating system credential service, Obsidian,
backup/sync software, agents, or other programs you direct at the collection. Review those
products' privacy terms separately.

See [compliance and scope](docs/compliance.md) for supported and excluded uses.
