# Quick Start - CI/CD Pipeline

## 🚀 Deploy to DietPi

```bash
# One-command deployment with all safety checks
./deploy_dietpi.sh
```

This will:
1. ✅ Run all CI tests
2. ✅ Commit your changes
3. ✅ Create backup on DietPi
4. ✅ Push to git
5. ✅ Deploy to DietPi
6. ✅ Restart bot service
7. ✅ Verify health (auto-rollback if fails)

## 🔄 Rollback

If something goes wrong:
```bash
./rollback_dietpi.sh
```

## 🧪 Test Before Deploy

```bash
./ci_test.sh
```

## 📚 Full Documentation

See [CI_CD_GUIDE.md](CI_CD_GUIDE.md) for complete documentation.

## Configuration

Set these environment variables if needed:
```bash
export DIETPI_USER=dietpi
export DIETPI_HOST=dietpi.local
export DIETPI_PATH=/home/dietpi/aroma
```
