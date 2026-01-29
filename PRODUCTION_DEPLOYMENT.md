# 🚀 Production Deployment Guide

## Pre-Deployment Checklist

### 1. Local Testing
- [ ] All tests passing: `./ci_test.sh`
- [ ] Docker build successful: `docker-compose build`
- [ ] Docker containers running: `docker-compose up -d`
- [ ] Database initialized: `./init_docker_db.sh`
- [ ] Health check passed: `./docker_health_check.sh`

### 2. Code Review
- [ ] All changes committed
- [ ] Code reviewed and approved
- [ ] No debug statements or TODOs
- [ ] Documentation updated

### 3. Configuration
- [ ] `.env` file configured for production
- [ ] Database credentials secure
- [ ] Telegram token valid
- [ ] DietPi SSH access working

## Deployment Steps

### Option 1: Docker Deployment (Recommended)

#### First-Time Setup on DietPi

```bash
# 1. SSH to DietPi
ssh dietpi@dietpi.local

# 2. Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker dietpi
sudo systemctl enable docker
sudo systemctl start docker

# 3. Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose

# 4. Clone repository
cd ~
git clone <your-repo-url> aroma
cd aroma

# 5. Configure environment
cp .env.example .env
nano .env  # Edit with production values

# 6. Build and start
docker-compose build
docker-compose up -d

# 7. Initialize database
./init_docker_db.sh

# 8. Verify
./docker_health_check.sh
```

#### Subsequent Deployments

From your local machine:

```bash
# Deploy with one command
./docker_deploy.sh
```

This will:
1. ✅ Run CI tests
2. ✅ Build Docker image
3. ✅ Tag with version
4. ✅ Commit and push to git
5. ✅ Transfer image to DietPi
6. ✅ Blue-green deployment
7. ✅ Health check
8. ✅ Auto-rollback if fails

### Option 2: Traditional Deployment (Legacy)

```bash
# Deploy without Docker
./deploy_dietpi.sh
```

## Post-Deployment

### 1. Verify Deployment

```bash
# Check container status
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose ps"

# Check logs
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose logs -f aroma_bot"

# Health check
ssh dietpi@dietpi.local "cd ~/aroma && ./docker_health_check.sh"
```

### 2. Test Critical Features

- [ ] Bot responds to /start
- [ ] User registration works
- [ ] Combat system functional
- [ ] Database queries working
- [ ] No error logs

### 3. Monitor

```bash
# Real-time logs
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose logs -f"

# Resource usage
ssh dietpi@dietpi.local "docker stats"

# Database size
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec postgres psql -U alan -d aroma_bot -c 'SELECT pg_size_pretty(pg_database_size(current_database()));'"
```

## Rollback Procedure

If something goes wrong:

```bash
# Quick rollback
./docker_rollback.sh

# Or manually
ssh dietpi@dietpi.local "cd ~/aroma && docker images aroma-bot"
# Note the previous version tag
ssh dietpi@dietpi.local "cd ~/aroma && docker tag aroma-bot:PREVIOUS_VERSION aroma-bot:latest && docker-compose restart"
```

## Database Management

### Backup

```bash
# Automated backup
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec postgres pg_dump -U alan aroma_bot > backup_\$(date +%Y%m%d).sql"

# Download backup locally
scp dietpi@dietpi.local:~/aroma/backup_*.sql ./backups/
```

### Restore

```bash
# Upload backup
scp ./backups/backup_20260129.sql dietpi@dietpi.local:~/aroma/

# Restore
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec -T postgres psql -U alan -d aroma_bot < backup_20260129.sql"
```

### Import Production Data

```bash
# Export from test database
PGPASSWORD=asd1XD2LoL3 pg_dump -h localhost -U alan -d aroma_bot_test \
  --data-only --no-owner --no-acl > production_data.sql

# Transfer to DietPi
scp production_data.sql dietpi@dietpi.local:~/aroma/

# Import
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec -T postgres psql -U alan -d aroma_bot < production_data.sql"
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose logs"

# Rebuild
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose down && docker-compose build --no-cache && docker-compose up -d"
```

### Database Connection Issues

```bash
# Check database is running
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose ps postgres"

# Check database exists
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec postgres psql -U alan -l"

# Recreate database
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec postgres createdb -U alan aroma_bot"
```

### Out of Disk Space

```bash
# Clean old images
ssh dietpi@dietpi.local "docker system prune -a"

# Check disk usage
ssh dietpi@dietpi.local "df -h"
```

## Monitoring Setup (Optional)

### Grafana + Prometheus

```bash
# Add to docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

### Log Aggregation

```bash
# View aggregated logs
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose logs --tail=100 -f | grep ERROR"
```

## Security Checklist

- [ ] Firewall configured (only necessary ports open)
- [ ] SSH key authentication enabled
- [ ] Database password strong and unique
- [ ] Telegram token not in git
- [ ] Regular backups scheduled
- [ ] Docker containers running as non-root
- [ ] Network isolation enabled

## Maintenance Schedule

### Daily
- Check error logs
- Monitor resource usage

### Weekly
- Database backup
- Update dependencies if needed
- Review performance metrics

### Monthly
- Full system backup
- Security updates
- Capacity planning review

## Emergency Contacts

- **System Admin**: [Your contact]
- **Database Admin**: [Your contact]
- **On-Call**: [Your contact]

## Useful Commands

```bash
# Quick status check
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose ps && docker stats --no-stream"

# Restart bot only
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose restart aroma_bot"

# View recent errors
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose logs --tail=50 aroma_bot | grep -i error"

# Database shell
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec postgres psql -U alan -d aroma_bot"

# Bot shell
ssh dietpi@dietpi.local "cd ~/aroma && docker-compose exec aroma_bot /bin/bash"
```

## Success Criteria

Deployment is successful when:
- ✅ All containers healthy
- ✅ Bot responds to commands
- ✅ No errors in logs (last 100 lines)
- ✅ Database queries working
- ✅ Resource usage normal (<50% CPU, <1GB RAM)
- ✅ Health check passes

---

**Remember**: Always test in staging before deploying to production!
