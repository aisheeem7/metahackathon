# Deployment Guide

## Local Development

### 1. Start Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Tests
```bash
python scripts/validate_env.py
```

### 3. Start Server
```bash
python app.py
# or
python -m backend.app
```

Server runs on http://localhost:7860

---

## Docker Deployment

### Build Image
```bash
docker build -t expense-optimizer:latest .
```

### Run Container
```bash
docker run -p 7860:7860 \
  --env OPENAI_API_KEY="sk-..." \
  expense-optimizer:latest
```

### Health Check
```bash
curl http://localhost:7860/health
```

---

## HuggingFace Spaces Deployment

### Option A: Manual Deployment

1. **Create HF Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Select "Docker" runtime
   - Name it: `personal-expense-optimizer`

2. **Link to GitHub**
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/personal-expense-optimizer
   git push hf main
   ```

3. **Configure Space Settings**
   - SDK: Docker
   - Persistent storage: Optional (10GB available)
   - Private: Toggle as needed

### Option B: GitHub Actions Auto-Deployment

1. **Create HF Token**
   - Go to https://huggingface.co/settings/tokens
   - Create "write" access token
   - Copy token

2. **Add Secrets to GitHub**
   - Go to your GitHub repo
   - Settings → Secrets and variables → Actions
   - Add `HF_TOKEN` with your token
   - Add `HF_SPACE_ID` = `username/space-name`

3. **Enable Workflow**
   - Push to main branch
   - GitHub Actions auto-deploys to HF Spaces

---

## Environment Variables

### Required (for baseline)
```bash
OPENAI_API_KEY=sk-...  # Your OpenAI API key
```

### Optional
```bash
OPENAI_MODEL=gpt-4o-mini  # Default model
PORT=7860                 # Server port
DEBUG=false              # Debug mode
```

---

## Monitoring

### Health Check
```bash
curl http://localhost:7860/health
# {"status": "healthy"}
```

### Logs
```bash
# Local
python app.py  # see stdout

# Docker
docker logs <container-id>

# HF Spaces
# Visible in Space settings → Logs
```

### Performance
- Cold start: ~2-3s
- Warm start: <100ms
- Request handling: <1s per API call
- Memory usage: ~200MB idle

---

## Troubleshooting

### Import Errors
```bash
# Ensure parent directory is in path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -c "from env.finance_env import PersonalExpenseOptimizer"
```

### Port Already in Use
```bash
# Change port
python -c "from backend.app import app; app.run(port=8080)"

# Or kill process
lsof -ti:7860 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :7860    # Windows
```

### Docker Build Fails
```bash
# Clear cache
docker system prune -a

# Rebuild
docker build --no-cache -t expense-optimizer .
```

### Model Loading Issues
```bash
# Ensure API key is set
echo $OPENAI_API_KEY

# Test connection
python -c "import openai; openai.OpenAI()"
```

---

## Performance Metrics

| Operation | Time | Memory |
|-----------|------|--------|
| Environment init | ~50ms | ~10MB |
| reset() | ~10ms | <1MB |
| step() | ~5ms | <1MB |
| API request | ~100ms | <5MB |
| Full episode (30 steps) | ~200ms | <20MB |

---

## Scaling

### Concurrent Users
- Single instance: ~10-50 concurrent
- Multi-instance: Use load balancer
- HF Spaces: Auto-scales based on traffic

### GPU Acceleration
Not required - CPU-only is sufficient.

---

## Backup & Recovery

### Backup Results
```bash
# Save baseline scores
cp results/baseline_scores.json backups/baseline_$(date +%Y%m%d).json
```

### Environment Rollback
```bash
git checkout HEAD~1  # Previous version
docker build -t expense-optimizer .
```

---

## Next Steps

1. Deploy to HF Spaces
2. Test all endpoints work
3. Submit to hackathon
4. Monitor performance
5. Gather user feedback

---

**For questions or issues:** Create a GitHub issue or comment on the HF Space.
