# X developer app setup

Wikix does not provide credentials. Each collection owner must create an approved app, fund API
usage, and comply with X's current terms.

The exact X Developer Console labels and commercial terms can change. Verify them against current
[X OAuth documentation](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code)
and [bookmark endpoint documentation](https://docs.x.com/x-api/users/get-bookmarks).

## Configure the app

1. Create or select a project and app in the
   [X Developer Console](https://developer.x.com/en/portal/dashboard).
2. Enable OAuth 2.0 and Authorization Code with PKCE. Wikix is a public native/desktop client and
   does not use a client secret.
3. Add the exact callback URI for the configured port. The default is:

   ```text
   http://127.0.0.1:8765/callback
   ```

4. Allow only these scopes:

   ```text
   bookmark.read tweet.read users.read offline.access
   ```

5. Ensure the app has access to the bookmark endpoint and that the developer account has sufficient
   API credits.
6. Set an X Developer Console spending limit before the first sync.
7. Copy the OAuth 2.0 client ID. Do not put a client secret into Wikix.

Initialize the collection with the same callback port:

```shell
wikix init PATH --client-id YOUR_CLIENT_ID --callback-port 8765
```

Then run:

```shell
cd PATH
wikix auth login
```

Wikix opens the system browser, verifies the OAuth state value, receives the localhost callback,
exchanges the PKCE verifier, and binds that collection to the authenticated X account. Use a
separate collection directory for each account.

## Headless environments

The interactive callback flow requires a local browser and callback port. For a headless process,
obtain user-context tokens through an appropriate secure workflow and inject:

```shell
export WIKIX_ACCESS_TOKEN=...
export WIKIX_REFRESH_TOKEN=...
wikix --collection PATH sync
```

Do not put tokens in shell history, `.env` files, collection configuration, CI logs, or source
control. Wikix has no plaintext credential fallback.
