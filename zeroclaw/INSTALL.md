# ZeroClaw Installation

ZeroClaw binary (~8.5MB) is not committed here due to size. Download it:

```
mkdir -p ~/.cargo/bin
curl -fsSL https://github.com/zeroclaw-labs/zeroclaw/releases/download/v0.5.4/zeroclaw-x86_64-unknown-linux-gnu.tar.gz | tar -xz
cp zeroclaw ~/.cargo/bin/
```

Or use the install script:
```
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/master/install.sh | bash -- --prefer-prebuilt
```

## Setup

1. Create directories:
   ```
   mkdir -p ~/.zeroclaw/workspace/{sessions,memory,state,cron,skills}
   ```

2. Clone open-skills repo (for bundled skills):
   ```
   git clone --depth 1 https://github.com/besoeasy/open-skills ~/open-skills
   ```

3. Copy config:
   ```
   cp zeroclaw/config.toml ~/.zeroclaw/config.toml
   # Edit ~/.zeroclaw/config.toml and add:
   #   - NVIDIA_API_KEY env var in systemd service
   #   - Telegram bot_token (from @BotFather)
   ```

4. Copy workspace files:
   ```
   cp -r zeroclaw/workspace/* ~/.zeroclaw/workspace/
   ```

4. Install systemd service:
   ```
   sudo cp zeroclaw/zeroclaw.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now zeroclaw
   ```

5. Access dashboard at http://127.0.0.1:42618 (or via cloudflared tunnel)
