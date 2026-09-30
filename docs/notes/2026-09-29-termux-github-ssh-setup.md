# Termux + GitHub SSH Setup (phone)

**Status: WORKING** — hangul-tutor runs on the phone via Termux.
Written 2026-09-29. This records a confirmed-working configuration, not a plan.

## What this covers
Running hangul-tutor from an Android phone: Termux, Python, and SSH access to
GitHub so the phone clone can pull/push without a password.

## Confirmed working: SSH auth

Test output was:

    Hi eemoogee! You've successfully authenticated

That line is the definitive confirmation the key setup is correct.

**`GitHub does not provide shell access.` is NORMAL.**
It is not an error — GitHub only allows git operations over SSH, not a shell.
Seeing this message during the auth test means everything is set up right.

## Python on the phone

Python was installed into Termux (not a system/root Python).

Launch the app with:

    python hangul_cli.py

(Run from inside the cloned repo directory.)

## Clone a repo

Get the SSH URL from GitHub: **Code → SSH**

    git@github.com:eemoogee/hangul-tutor.git

Then in Termux:

    cd ~/downloads
    git clone git@github.com:eemoogee/hangul-tutor.git

(Or clone straight into home: `cd ~` first.)

You should NOT be asked for a username or password. If you ARE asked, the SSH
key isn't being picked up — see Troubleshooting below.

## Verify the clone

    cd hangul-tutor
    git remote -v

Expected:

    origin  git@github.com:eemoogee/hangul-tutor.git (fetch)
    origin  git@github.com:eemoogee/hangul-tutor.git (push)

## Daily workflow (no password ever)

    git pull
    git add .
    git commit -m "message"
    git push

## Troubleshooting

- **Asked for a password** → SSH key not loaded. Check with
  `ssh -T git@github.com` — it should greet you by username.
- **Wrong remote URL** → fix with
  `git remote set-url origin git@github.com:eemoogee/NEW_REPO.git`
- **"GitHub does not provide shell access"** → normal, ignore.
- **Import errors for a package on the phone** → the Termux Python is separate
  from the laptop's; install missing deps in Termux (`pip install <pkg>`).
  (Not yet verified — recorded as a likely future snag.)

## Open items / for a future session

- No dedicated folder yet for **phone-related coding tech notes** generally.
  This file lives in `docs/notes/` as a first entry; may want its own home
  (e.g. a `phone/` category) later.
- Not yet recorded here: the exact Termux setup steps used *before* Python was
  installed (package installs, storage permissions, etc.). Add if rebuilding
  from scratch on a new device.
