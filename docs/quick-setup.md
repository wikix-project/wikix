# Quick setup

Wikix runs locally and writes Markdown notes and JSONL to a collection directory you control.
Use this short path after preparing your own X developer app.

## Before you begin

Have all of the following ready:

- Python 3.12 or newer
- An approved X developer project and app with OAuth 2.0 Authorization Code with PKCE
- The `bookmark.read`, `tweet.read`, `users.read`, and `offline.access` scopes
- API credits and a spending limit

The first sync scans the complete current bookmark collection. Review current pricing in the
[X Developer Console](https://developer.x.com/en/portal/dashboard) before confirming the API call.
Replace `YOUR_CLIENT_ID` and the collection path with your own values.

## Run these commands

Run the commands in order:

```shell
uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git
wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID
cd ~/Documents/MyVault/X-Bookmarks
wikix auth login
wikix sync
```

## What happens next

Wikix opens X in your system browser for local OAuth, stores tokens in the operating-system
credential store, and writes the current export to the collection directory. Personal notes survive
normal syncs, while incomplete snapshots and managed-content conflicts are protected.

For callback configuration, detailed cost guidance, collection layout, recovery behavior, and later
sync options, read the [full Step-by-Step Guide](getting-started.md).
