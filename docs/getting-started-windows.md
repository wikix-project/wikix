# Install and use Wikix on Windows

This guide assumes you have never used Python, Git, or PowerShell. Complete the steps in order.

## What you will do

You will create an X developer app for your own account, add API credits, install Wikix, sign in
through X, and export your bookmarks to files on your Windows computer.

## 1. Confirm what you need

You will need:

- a valid X account that you can sign in to and whose bookmarks you want to export;
- a payment method accepted by the X Developer Console;
- a Windows computer with internet access and a browser;
- access to Windows credential storage;
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
in every two hours. The callback works only on your Windows computer and is not a hosted Wikix
service.

## 5. Copy your Client ID

Open the app's keys, tokens, or OAuth 2.0 credentials area and copy the **Client ID** into a
temporary note. You will replace `YOUR_CLIENT_ID` with it later.

The Client ID is not the API Key, Bearer Token, Access Token, or Client Secret. Wikix never asks
for the Client Secret. Keep every secret credential in a password manager.

## 6. Open PowerShell

1. Press the **Windows** key.
2. Type **PowerShell**.
3. Open **Windows PowerShell** or **PowerShell**. Do not open Command Prompt.

Copy one command at a time into PowerShell and press **Enter**. Do not copy the `PS>` prompt that
some websites display before commands.

## 7. Install and verify Git

Run:

```powershell
winget install --id Git.Git -e --source winget
```

Accept the installer prompt if Windows shows one. Close PowerShell and open it again, then run:

```powershell
git --version
```

Success looks like `git version ...windows...`.

If `winget` is unavailable, download Git from the
[official Git for Windows page](https://git-scm.com/download/win), run the installer with its
default options, reopen PowerShell, and run `git --version` again.

## 8. Install and verify uv

`uv` installs Wikix and a compatible Python version without making you configure Python yourself.
Run:

```powershell
winget install --id=astral-sh.uv -e
```

If that WinGet package is unavailable, run Astral's official one-time installer instead:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

This bypass applies only to that installer process; do not permanently weaken PowerShell's
execution policy.

Close PowerShell and open it again. Then run:

```powershell
uv --version
```

Success looks like `uv x.y.z`, with numbers in place of `x.y.z`.

## 9. Install and verify Wikix

Run:

```powershell
uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git
```

Make the installed command available in future PowerShell windows:

```powershell
uv tool update-shell
```

Close PowerShell and open it again. Then run:

```powershell
wikix --version
```

Success is:

```text
Wikix 0.1.0
```

## 10. Create your bookmark collection

In the next command, replace only `YOUR_CLIENT_ID` with the Client ID copied in step 5. Keep the
quotation marks:

```powershell
wikix init "$HOME\Documents\X-Bookmarks" --client-id "YOUR_CLIENT_ID"
```

Success begins with `Initialized Wikix collection at`.

Move PowerShell into the new collection:

```powershell
Set-Location "$HOME\Documents\X-Bookmarks"
```

A successful `Set-Location` command usually prints nothing.

## 11. Sign in to X

Run:

```powershell
wikix auth login
```

Your browser opens X. Confirm that you are signing in to the bookmark-owning account, review the
permissions, and approve access. Return to PowerShell. Success begins with
`Authenticated X account`. Wikix stores the resulting tokens in Windows credential storage.

## 12. Export your bookmarks

Run the default lean export:

```powershell
wikix sync
```

The first sync says its bookmark-count estimate is unknown because no earlier export exists. Review
the cost message and type `y` only if you want to continue. Success begins with `Synced`.

Every later sync scans the complete collection again and can incur another charge. `--rich` and
`--folders` are optional modes with additional, unpredictable resource costs; leave them off for
the lowest-cost export.

## 13. Open your exported files

Run:

```powershell
explorer.exe "$HOME\Documents\X-Bookmarks"
```

File Explorer opens the folder. Your Markdown notes are in `bookmarks\`, and the machine-readable
export is `bookmarks.jsonl`. You can read the Markdown files directly; Obsidian is optional.

## 14. Run Wikix again later

Open PowerShell, return to the collection, and check it:

```powershell
Set-Location "$HOME\Documents\X-Bookmarks"
```

```powershell
wikix status
```

Then run another complete scan when you are ready to pay for it:

```powershell
wikix sync
```

## Troubleshooting

- **`winget` is not recognized:** install Git from
  [Git for Windows](https://git-scm.com/download/win), then use the official Astral installer shown
  in step 8 for uv.
- **PowerShell blocks the uv installer:** copy the exact one-time command from step 8. Do not
  permanently change the system execution policy.
- **`git` is not recognized:** close every PowerShell window, reopen PowerShell, and rerun
  `git --version`.
- **`uv` is not recognized:** reopen PowerShell after installation and rerun `uv --version`.
- **`wikix` is not recognized:** reopen PowerShell, rerun the install command in step 9, and then
  run `uv tool update-shell`. Reopen PowerShell once more and rerun `wikix --version`.
- **Callback URI mismatch:** make the app callback exactly
  `http://127.0.0.1:8765/callback`, save it, and rerun `wikix auth login`.
- **Port 8765 is already in use:** choose an unused port such as `8766`, add
  `http://127.0.0.1:8766/callback` to the X app, and open
  `$HOME\Documents\X-Bookmarks\.wikix\config.toml` in Notepad. Change
  `callback_port = 8765` to `callback_port = 8766`, save the file, and rerun
  `wikix auth login`. Do not run `wikix init` again for an existing collection.
- **Missing or rejected scopes:** enable `bookmark.read`, `tweet.read`, `users.read`, and
  `offline.access`, save the app, and sign in again.
- **Credential storage is locked or unavailable:** unlock Windows with your normal account and
  rerun `wikix auth login`; do not substitute a plaintext token file.
- **HTTP 403 or an access error:** confirm that the app belongs to the signed-in account, bookmark
  access is enabled, credits remain, and the spending limit has not been reached.
- **Out of credits:** add credits in the Developer Console before retrying. Wikix cannot bypass X
  billing.
- **HTTP 429:** for one API request, Wikix waits at most three times and 900 seconds total. A
  missing, invalid, or non-finite reset time uses a 60-second wait; valid finite reset times wait
  at least one second. This rate-limit budget is independent from transient network and 5xx
  retries. If it is exhausted, the sync exits without changing the existing export; rerun
  `wikix sync` later to resume compatible staging.
- **The sync was interrupted:** run `wikix sync` again from the same collection so compatible
  staged progress can resume.
- **A managed-content conflict is reported:** open the named file and resolve the reported edit;
  Wikix deliberately leaves conflicting files untouched.

Never paste X tokens or secrets into a collection file, `.env` file, PowerShell command, or support
message.
