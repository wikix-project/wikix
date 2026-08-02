# Install and use Wikix on macOS

This guide assumes you have never used Python, Git, or Terminal. Complete the steps in order.

## What you will do

You will create an X developer app for your own account, add API credits, install Wikix, sign in
through X, and export your bookmarks to files on your Mac.

## 1. Confirm what you need

You will need:

- a valid X account that you can sign in to and whose bookmarks you want to export;
- a payment method accepted by the X Developer Console;
- a Mac with internet access and a browser;
- access to macOS Keychain;
- about 20–30 minutes for first-time setup.

Wikix uses the official X API. It does not ask for your X password, scrape the X website, or store
tokens in plain text.

## 2. Create your X developer account and app

1. Open [X Developer Console](https://console.x.com) in your browser.
2. Sign in with the same X account whose bookmarks you want to export.
3. If X asks you to enroll, accept the Developer Agreement and complete the requested profile
   information.
4. From the Developer Console, create a new app. X's public guide currently calls this **New App**.
5. Enter a name, description, and personal bookmark-export use case.
6. Save any credentials X shows in a password manager. Wikix will use only the OAuth 2.0 Client ID.

X changes Console wording occasionally. If a label differs, use the equivalent current app,
billing, or user-authentication section. Do not create a second app if you already have one owned
by this same X account.

## 3. Add API credits and a spending limit

Open the billing or credits area for your developer account. Purchase the minimum credit amount
currently displayed, then set a spending limit you are comfortable with before exporting.

X's public pricing documentation says there is no subscription or minimum ongoing spend. If the
smallest top-up shown to you is **$5**, that amount covers up to 5,000 lean owned bookmark reads at
the currently documented price of **$0.001 per returned bookmark**.

The bookmark API can return up to 100 bookmarks in one request, but X still bills each returned
bookmark resource. For example, 100 returned bookmarks cost about $0.10, not $0.001.

These estimates were checked on July 29, 2026 and are not a price guarantee. Taxes, changed X
prices, optional rich data, bookmark folders, and later complete scans can add cost. Each Wikix
sync scans the complete bookmark collection. Check the current price shown in the Console.

## 4. Configure OAuth for Wikix

Open your app's user-authentication settings and enable **OAuth 2.0 Authorization Code with PKCE**.
Configure a public native or desktop client if the Console asks for an app type.

Enter this exact callback URL:

```text
http://127.0.0.1:8765/callback
```

Enable these four scopes:

```text
bookmark.read tweet.read users.read offline.access
```

Save the settings. `offline.access` lets Wikix refresh an expired login without asking you to sign
in every two hours. The callback works only on your Mac and is not a hosted Wikix service.

## 5. Copy your Client ID

Open the app's keys, tokens, or OAuth 2.0 credentials area and copy the **Client ID** into a
temporary note. You will replace `YOUR_CLIENT_ID` with it later.

The Client ID is not the API Key, Bearer Token, Access Token, or Client Secret. Wikix never asks
for the Client Secret. Keep every secret credential in a password manager.

## 6. Open Terminal

1. Press **Command–Space** to open Spotlight.
2. Type **Terminal**.
3. Press **Return**.

The window that opens accepts the commands below. Copy one command at a time, paste it, and press
**Return**. Do not type the `$` character that some websites show before commands.

## 7. Install and verify Git

Run:

```shell
git --version
```

If macOS asks to install Command Line Developer Tools, choose **Install**, wait for it to finish,
and run the same command again. Success begins with `git version`.

## 8. Install and verify uv

`uv` installs Wikix and a compatible Python version without making you configure Python yourself.
Run Astral's official installer:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

When it finishes, close Terminal and open it again. Then run:

```shell
uv --version
```

Success looks like `uv x.y.z`, with numbers in place of `x.y.z`.

## 9. Install and verify Wikix

Run:

```shell
uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git
```

Then run:

```shell
wikix --version
```

Success is:

```text
Wikix 0.1.0
```

## 10. Create your bookmark collection

In the next command, replace only `YOUR_CLIENT_ID` with the Client ID copied in step 5. Keep the
quotation marks:

```shell
wikix init "$HOME/Documents/X-Bookmarks" --client-id "YOUR_CLIENT_ID"
```

Success begins with `Initialized Wikix collection at`.

Move Terminal into the new collection:

```shell
cd "$HOME/Documents/X-Bookmarks"
```

A successful `cd` command usually prints nothing.

## 11. Sign in to X

Run:

```shell
wikix auth login
```

Your browser opens X. Confirm that you are signing in to the bookmark-owning account, review the
permissions, and approve access. Return to Terminal. Success begins with `Authenticated X account`.
Wikix stores the resulting tokens in macOS Keychain.

## 12. Export your bookmarks

Run the default lean export:

```shell
wikix sync
```

The first sync says its bookmark-count estimate is unknown because no earlier export exists. Review
the cost message and type `y` only if you want to continue. Success begins with `Synced`.

Every later sync scans the complete collection again and can incur another charge. `--rich` and
`--folders` are optional modes with additional, unpredictable resource costs; leave them off for
the lowest-cost export.

## 13. Open your exported files

Run:

```shell
open "$HOME/Documents/X-Bookmarks"
```

Finder opens the folder. Your Markdown notes are in `bookmarks/`, and the machine-readable export
is `bookmarks.jsonl`. You can read the Markdown files directly; Obsidian is optional.

## 14. Run Wikix again later

Open Terminal, return to the collection, and check it:

```shell
cd "$HOME/Documents/X-Bookmarks"
```

```shell
wikix status
```

Then run another complete scan when you are ready to pay for it:

```shell
wikix sync
```

## Troubleshooting

- **`git: command not found`:** run `git --version`, accept the macOS Command Line Tools prompt,
  finish the installation, and reopen Terminal.
- **`uv: command not found`:** close every Terminal window, open Terminal again, and rerun
  `uv --version`.
- **`wikix: command not found`:** reopen Terminal, rerun the install command in step 9, and then
  rerun `wikix --version`.
- **Callback URI mismatch:** make the app callback exactly
  `http://127.0.0.1:8765/callback`, save it, and rerun `wikix auth login`.
- **Port 8765 is already in use:** choose an unused port such as `8766`, add
  `http://127.0.0.1:8766/callback` to the X app, and open
  `$HOME/Documents/X-Bookmarks/.wikix/config.toml` in a text editor. Change
  `callback_port = 8765` to `callback_port = 8766`, save the file, and rerun
  `wikix auth login`. Do not run `wikix init` again for an existing collection.
- **Missing or rejected scopes:** enable `bookmark.read`, `tweet.read`, `users.read`, and
  `offline.access`, save the app, and sign in again.
- **Keychain is locked or unavailable:** unlock your login Keychain in the **Passwords** app or
  **Keychain Access**, then rerun `wikix auth login`.
- **HTTP 403 or an access error:** confirm that the app belongs to the signed-in account, bookmark
  access is enabled, credits remain, and the spending limit has not been reached.
- **Out of credits:** add credits in the Developer Console before retrying. Wikix cannot bypass X
  billing.
- **HTTP 429:** leave Wikix running so it can wait for X's reset, or retry after the displayed
  reset time.
- **The sync was interrupted:** run `wikix sync` again from the same collection so compatible
  staged progress can resume.
- **A managed-content conflict is reported:** open the named file and resolve the reported edit;
  Wikix deliberately leaves conflicting files untouched.

Never paste X tokens or secrets into a collection file, `.env` file, shell command, or support
message.
