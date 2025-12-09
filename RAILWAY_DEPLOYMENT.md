# Railway Deployment Guide - Docker Build Method

This guide will help you deploy the Satyasetu Chatbot to Railway using the Docker build method.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code should be pushed to GitHub
3. **MongoDB Database**: Set up MongoDB (Railway MongoDB addon or MongoDB Atlas)

## Step 1: Prepare Your Repository

The following files have been created for Railway deployment:
- `Dockerfile` - Defines the container image
- `.dockerignore` - Excludes unnecessary files from the build
- `railway.json` - Railway-specific configuration

## Step 2: Push to GitHub

Make sure all changes are committed and pushed:

```bash
git add Dockerfile .dockerignore railway.json RAILWAY_DEPLOYMENT.md
git commit -m "Add Railway Docker deployment configuration"
git push origin main
```

## Step 3: Create a New Project on Railway

1. Go to [railway.app/new](https://railway.app/new)
2. Click **"Deploy from GitHub repo"**
3. Select your repository: `SakshamSharma2005/satyasetu-chatbot`
4. Railway will detect the Dockerfile automatically

## Step 4: Add MongoDB Database

### Option A: Railway MongoDB Plugin (Recommended for Railway)
1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add MongoDB"**
3. Railway will automatically create a MongoDB instance
4. Copy the `MONGODB_URL` connection string provided

### Option B: MongoDB Atlas (Free tier available)
1. Create a cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Get your connection string
3. Whitelist Railway's IP addresses (or use 0.0.0.0/0 for allow all)

## Step 5: Configure Environment Variables

In your Railway project, go to **Variables** tab and add:

### Required Variables:
```env
# Application
APP_NAME=Satyasetu Chatbot
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False

# Security (IMPORTANT: Generate a secure secret key)
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Database (if using Railway MongoDB plugin, this is auto-set)
MONGODB_URL=${{MongoDB.MONGO_URL}}
MONGODB_DB_NAME=SatyaSetu

# Database URL (SQLite fallback - optional)
DATABASE_URL=sqlite:///./data/satyasetu.db

# Groq API (Get free key from https://console.groq.com)
GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL=llama-3.1-8b-instant

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db

# CORS (add your frontend domains)
CORS_ORIGINS=["https://your-frontend-domain.com","http://localhost:3000"]

# Models
TRANSLATION_MODEL=ai4bharat/indictrans2-en-indic-dist-200M
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Generate SECRET_KEY:
On your local machine, run:
```bash
# Linux/Mac/Git Bash
openssl rand -hex 32

# PowerShell
[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString()))
```

### Get GROQ_API_KEY:
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Create an API key

## Step 6: Deploy

1. Railway will automatically start building and deploying
2. Monitor the build logs in the **Deployments** tab
3. Once deployed, Railway will provide a public URL (e.g., `your-app.up.railway.app`)

## Step 7: Verify Deployment

Visit your Railway URL endpoints:
- `https://your-app.up.railway.app/` - Root endpoint
- `https://your-app.up.railway.app/health` - Health check
- `https://your-app.up.railway.app/docs` - API documentation

## Step 8: Initialize Database (Optional)

If you need to set up admin users or load sample data, you can use Railway's shell:

1. In Railway dashboard, click on your service
2. Go to **Settings** → **Deploy**
3. Use the shell to run setup scripts:

```bash
# Set admin user (if needed)
python set_admin_user.py

# Load sample data (optional)
python load_sample_data.py
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URL` | Yes | MongoDB connection string |
| `GROQ_API_KEY` | Yes | Groq API key for LLM |
| `SECRET_KEY` | Yes | JWT secret (use secure random key) |
| `CORS_ORIGINS` | No | Allowed frontend origins |
| `ENVIRONMENT` | No | `production` or `development` |
| `DEBUG` | No | `False` for production |

## Troubleshooting

### Build Fails
- Check the build logs in Railway dashboard
- Ensure all dependencies in `requirements.txt` are compatible
- Verify Dockerfile syntax

### App Crashes on Startup
- Check `MONGODB_URL` is correct
- Verify `GROQ_API_KEY` is valid
- Check application logs in Railway dashboard

### Database Connection Issues
- Verify MongoDB is running
- Check MongoDB connection string format
- Ensure IP whitelist includes Railway's IPs (or use 0.0.0.0/0)

### Port Binding Issues
- Railway automatically sets `PORT` environment variable
- Dockerfile uses `${PORT:-8080}` to read Railway's port

## Scaling & Performance

Railway's free tier includes:
- 500 hours/month runtime
- Automatic SSL/HTTPS
- Custom domains
- Auto-deployments on git push

For production workloads, consider upgrading to Railway Pro for:
- Unlimited runtime
- More resources
- Priority support

## Monitoring

Access logs in Railway dashboard:
- **Deployments** tab - Build logs
- **Observability** tab - Application logs
- **Metrics** tab - CPU, Memory, Network usage

## Continuous Deployment

Railway automatically deploys when you push to your GitHub main branch:
1. Make changes locally
2. Commit and push to GitHub
3. Railway detects changes and rebuilds
4. New version deploys automatically

## Cost Optimization

To minimize costs on Railway:
- Use Railway's MongoDB addon (free tier)
- Use efficient Groq models (llama-3.1-8b-instant)
- Keep ChromaDB size manageable
- Monitor usage in Railway dashboard

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Project Issues: GitHub repository issues

---

**Important Security Notes:**
- Never commit `.env` files with secrets to Git
- Use strong, unique `SECRET_KEY` in production
- Restrict CORS origins to your actual frontend domains
- Keep API keys secure and rotate them periodically
