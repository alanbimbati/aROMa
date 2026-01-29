# CI/CD Pipeline Documentation

## Overview
This CI/CD pipeline ensures code quality and safe deployment to DietPi with automatic rollback capabilities.

## Components

### 1. Pre-commit Hook (`.git/hooks/pre-commit`)
Runs automatically before each commit:
- ✅ Python syntax validation
- ✅ Import checks
- ✅ Debug statement detection

### 2. CI Test Runner (`ci_test.sh`)
Comprehensive test suite that must pass before deployment:
- ✅ Python syntax check
- ✅ Import validation
- ✅ Defense system tests
- ✅ PvE system tests
- ✅ Combat mechanics tests
- ✅ Code quality checks

**Usage:**
```bash
./ci_test.sh
```

### 3. Deployment Script (`deploy_dietpi.sh`)
Safe deployment to DietPi with automatic rollback:

**Steps:**
1. Run CI tests locally
2. Commit changes
3. Create backup on DietPi
4. Push to git
5. Pull on DietPi
6. Restart bot service
7. Health check (auto-rollback on failure)

**Usage:**
```bash
./deploy_dietpi.sh
```

**Environment Variables:**
- `DIETPI_USER`: SSH user (default: dietpi)
- `DIETPI_HOST`: SSH host (default: dietpi.local)
- `DIETPI_PATH`: Bot path on DietPi (default: /home/dietpi/aroma)

**Example:**
```bash
DIETPI_HOST=192.168.1.100 ./deploy_dietpi.sh
```

### 4. Rollback Script (`rollback_dietpi.sh`)
Restore previous version if issues occur:

**Usage:**
```bash
./rollback_dietpi.sh
```

## Workflow

### Normal Deployment
```bash
# 1. Make changes
vim services/pve_service.py

# 2. Test locally
./ci_test.sh

# 3. Deploy to DietPi
./deploy_dietpi.sh
# (will prompt for commit message)
```

### Emergency Rollback
```bash
./rollback_dietpi.sh
# (will show available backups and restore the latest)
```

## Safety Features

### Automatic Rollback
The deployment script automatically rolls back if:
- CI tests fail locally
- Git push fails
- Pull on DietPi fails
- Service restart fails
- Health check fails

### Backup System
- Backups are created before each deployment
- Stored in `/tmp/aroma_backup_YYYYMMDD_HHMMSS/`
- Can be manually restored using `rollback_dietpi.sh`

### Health Checks
- Service status verification after deployment
- 5-second grace period for startup
- Automatic rollback if service fails to start

## Best Practices

1. **Always run CI tests before deploying:**
   ```bash
   ./ci_test.sh && ./deploy_dietpi.sh
   ```

2. **Test changes locally first:**
   ```bash
   python3 main.py  # Test in local environment
   ```

3. **Monitor logs after deployment:**
   ```bash
   ssh dietpi@dietpi.local "sudo journalctl -u aroma-bot -f"
   ```

4. **Keep backups for at least 7 days:**
   Backups are stored in `/tmp/` - move important ones to permanent storage

## Troubleshooting

### Deployment Fails
1. Check CI test output for specific failures
2. Review error messages from deployment script
3. SSH to DietPi and check logs:
   ```bash
   ssh dietpi@dietpi.local
   sudo journalctl -u aroma-bot -n 100
   ```

### Service Won't Start
1. Check Python dependencies:
   ```bash
   ssh dietpi@dietpi.local "cd /home/dietpi/aroma && pip3 list"
   ```
2. Check for syntax errors:
   ```bash
   ssh dietpi@dietpi.local "cd /home/dietpi/aroma && python3 -m py_compile *.py"
   ```

### Rollback Issues
1. List available backups:
   ```bash
   ssh dietpi@dietpi.local "ls -lt /tmp/aroma_backup_*"
   ```
2. Manually restore if needed:
   ```bash
   ssh dietpi@dietpi.local "sudo systemctl stop aroma-bot && rm -rf /home/dietpi/aroma/* && cp -r /tmp/aroma_backup_XXXXXX/* /home/dietpi/aroma/ && sudo systemctl start aroma-bot"
   ```

## Configuration

### DietPi Service Setup
Ensure the systemd service is configured:
```bash
sudo systemctl status aroma-bot
```

If not configured, create `/etc/systemd/system/aroma-bot.service`:
```ini
[Unit]
Description=Aroma Telegram Bot
After=network.target

[Service]
Type=simple
User=dietpi
WorkingDirectory=/home/dietpi/aroma
ExecStart=/usr/bin/python3 /home/dietpi/aroma/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable aroma-bot
sudo systemctl start aroma-bot
```

## Maintenance

### Clean Old Backups
```bash
ssh dietpi@dietpi.local "find /tmp/aroma_backup_* -mtime +7 -exec rm -rf {} \;"
```

### Update Dependencies
```bash
ssh dietpi@dietpi.local "cd /home/dietpi/aroma && pip3 install -r requirements.txt --upgrade"
```
