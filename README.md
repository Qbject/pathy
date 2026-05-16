# Pathy
Personal telegram bot capable of
- notifying friends when they go online in Apex Legends,
- stat calculation
- new video notifications
- entertainment
- other features

## Running as a systemd service

Edit `systemd/pathy.service` — set `User`, `WorkingDirectory`, and `ExecStart` to match your deployment path, then:

```bash
sudo cp systemd/pathy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pathy
```