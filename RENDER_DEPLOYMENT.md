# Render Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Expense Analyzer application to Render.com using Docker containers with ephemeral storage.

## Prerequisites

- GitHub repository: `https://github.com/galak06/expense_anylizer`
- Render account (free tier available)
- All deployment files are pre-configured

## Deployment Files

The following files are already configured for Render deployment:

### `render.yaml`
- Service configuration with all environment variables
- Docker build settings
- Health check endpoint configuration
- Auto-deploy enabled

### `Dockerfile`
- Python 3.11 slim base image
- Optimized for production deployment
- Streamlit on port 8501
- Health check configuration
- Proper permissions and directory structure

### `.dockerignore`
- Excludes unnecessary files from Docker build
- Optimizes build time and image size
- Excludes documentation, tests, and temporary files

## Database Storage Strategy

**Current Configuration: Ephemeral Storage (Free Tier)**

- Database location: `/app/data/transactions.db`
- Data persists during app runtime
- Data resets when container restarts
- Perfect for testing and development
- Free to use

**Upgrade Options:**
- Persistent Disk: $0.25/GB/month
- External Database: PostgreSQL, Supabase, etc.

## Step-by-Step Deployment

### Step 1: Access Render Dashboard

1. Go to [https://dashboard.render.com/](https://dashboard.render.com/)
2. Sign in or create a free account
3. Connect your GitHub account if not already connected

### Step 2: Create Web Service

1. Click **"New +"** in the top navigation
2. Select **"Web Service"**
3. Choose **"Build and deploy from a Git repository"**
4. Select your repository: `galak06/expense_anylizer`

### Step 3: Configure Service

Render will automatically detect the `render.yaml` file and pre-populate all settings:

**Basic Settings:**
- **Name**: `expense-analyzer` (or your preferred name)
- **Environment**: `Docker`
- **Region**: `Oregon` (or closest to your users)
- **Branch**: `main`
- **Root Directory**: Leave empty

**Advanced Settings:**
- **Dockerfile Path**: `./Dockerfile` (auto-detected)
- **Docker Context**: `.` (current directory)
- **Plan**: `Starter` (free tier)

### Step 4: Environment Variables

All required environment variables are pre-configured in `render.yaml`:

**Core Application:**
- `STREAMLIT_SERVER_PORT=8501`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`
- `STREAMLIT_SERVER_HEADLESS=true`
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`
- `DATABASE_PATH=data/transactions.db`
- `LOG_LEVEL=INFO`

**Optional AI Features:**
- `OPENAI_API_KEY=your-openai-api-key-here` (add manually in dashboard)

**Application Configuration:**
- `FUZZY_MATCH_THRESHOLD=86`
- `KEYWORD_CONFIDENCE=0.95`
- `FUZZY_CONFIDENCE_THRESHOLD=0.8`
- `LLM_CONFIDENCE=0.75`
- `MIN_WORD_LENGTH=3`
- `ENCODINGS_LIST=utf-8,cp1255,iso-8859-8,windows-1255`
- `DELIMITERS_LIST=,,;,\t`
- `DEFAULT_MAPPING_PATH=data/mapping.csv`
- `MAX_FILE_SIZE_MB=10`

### Step 5: Deploy

1. Review all settings
2. Click **"Create Web Service"**
3. Wait for deployment (5-10 minutes)
4. Monitor build logs in the dashboard

### Step 6: Access Your Application

Once deployed, you'll receive a URL like:
`https://expense-analyzer-xyz.onrender.com`

## Monitoring and Management

### Health Checks
- Endpoint: `/_stcore/health`
- Automatically configured in Dockerfile
- Render monitors this endpoint for service health

### Logs
- Access build and runtime logs in Render dashboard
- Useful for debugging deployment issues
- Real-time log streaming available

### Service Management
- Start/stop service from dashboard
- View resource usage and metrics
- Configure custom domains (paid plans)

## Free Tier Limitations

**Important Considerations:**
- App sleeps after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds to wake up
- Database resets on every cold start
- 750 hours/month limit
- No persistent storage

**Workarounds:**
- Use external database for persistent data
- Upgrade to paid plan for always-on service
- Implement data export/import functionality

## Upgrading to Persistent Storage

### Option 1: Render Persistent Disk

1. Go to your service dashboard
2. Click **"Disks"** tab
3. Click **"Create Disk"**
4. Configure:
   - **Name**: `expense-analyzer-data`
   - **Size**: 1GB (minimum)
   - **Mount Path**: `/app/data`
5. Cost: $0.25/GB/month

### Option 2: External Database

Consider migrating to:
- **Render PostgreSQL**: $7/month managed database
- **Supabase**: Free tier with PostgreSQL
- **PlanetScale**: Free tier with MySQL

## Troubleshooting

### Common Issues

**Build Failures:**
- Check build logs in Render dashboard
- Verify all dependencies in `requirements.txt`
- Ensure Dockerfile syntax is correct

**Runtime Errors:**
- Check runtime logs
- Verify environment variables are set correctly
- Test health check endpoint

**Database Issues:**
- Remember data resets on container restart
- Consider upgrading to persistent storage
- Implement data backup/restore functionality

### Debug Commands

Test locally with Docker:
```bash
docker build -t expense-analyzer .
docker run -p 8501:8501 expense-analyzer
```

## Security Considerations

- Environment variables are encrypted in Render
- HTTPS is automatically provided
- No sensitive data in code repository
- API keys should be added via dashboard only

## Cost Optimization

**Free Tier:**
- Perfect for development and testing
- 750 hours/month included
- No persistent storage

**Paid Plans:**
- Starter: $7/month (always-on, persistent disk)
- Standard: $25/month (better performance)
- Pro: $85/month (production-ready)

## Next Steps

1. Deploy using the steps above
2. Test all application features
3. Monitor performance and logs
4. Consider upgrading to persistent storage for production use
5. Set up monitoring and alerts

## Support

- Render Documentation: [https://render.com/docs](https://render.com/docs)
- Render Support: Available in dashboard
- Application Issues: Check logs and health endpoints
