# Deploying autoedit on Fly.io with your domain

The app is one container: the web UI plus the job worker, with projects, models and your music/SFX
library on a persistent volume at `/data`. Everything is behind a password.

## One-time setup (from the repository root, on your computer)

```
brew install flyctl            # or: curl -L https://fly.io/install.sh | sh
fly auth login
fly apps create zerophilosophy-autoedit          # or another name; then change `app` in fly.toml
fly volumes create autoedit_data --region iad --size 50
fly secrets set AUTOEDIT_PASSWORD='pick-a-long-password' ANTHROPIC_API_KEY='sk-ant-...'
fly deploy
```

The app is then live at `https://zerophilosophy-autoedit.fly.dev`. Your browser asks for the password;
the user name can be anything.

## Your domain

`zerophilosophy.com` already points at another server (51.75.155.113), so use a subdomain to leave that site alone:

```
fly certs add edit.zerophilosophy.com
```

Then, at your DNS provider, add a `CNAME` record: name `edit`, value `zerophilosophy-autoedit.fly.dev`.
`fly certs show edit.zerophilosophy.com` reports when the HTTPS certificate is issued (usually minutes).
The app is then at `https://edit.zerophilosophy.com`.

## Updating

`fly deploy` again after pulling new code. Projects and the library on the volume survive deploys.

## Notes

- **Size and cost.** `fly.toml` asks for a `performance-2x` machine with 8 GB and keeps it running, because
  renders continue in the background after you close the tab. Check Fly's pricing page; to save money, run
  `fly scale count 0` when you are not editing and `fly scale count 1` before you are.
- **First run is slow.** The first project downloads the whisper model (about 500 MB for `small`) and the
  face model into `/data/models`. Set `AUTOEDIT_WHISPER__MODEL` in `fly.toml` to `medium` or `large-v3` for
  better words (needs more memory and time).
- **Music, SFX, avatars.** Upload them on the "Music & SFX" page; they go to `/data/assets/<profile>/...`.
- **Logs.** `fly logs` for the server; each job's log is linked from the Jobs page.
