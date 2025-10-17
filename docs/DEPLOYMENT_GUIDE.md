# 🚀 Render Deployment Guide

This guide walks you through deploying the Curser Expense Analyzer to Render.com using the provided `render.yaml` configuration.

## 📋 Prerequisites

1. **Render.com Account** - Sign up at [render.com](https://render.com)
2. **GitHub Repository** - Your code should be in a GitHub repository
3. **Dockerfile** - Ensure your `Dockerfile` is properly configured
4. **Environment Variables** - Review and customize the environment variables

## 🎯 Quick Deployment Steps

### 1. **Connect Repository**
1. Log into your Render dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository containing your code

### 2. **Configure Service**
1. **Name**: `expense-analyzer` (or your preferred name)
2. **Environment**: `Docker`
3. **Dockerfile Path**: `./Dockerfile`
4. **Docker Context**: `.`
5. **Plan**: `Starter` (free tier)

### 3. **Environment Variables**
The `render.yaml` file includes all necessary environment variables. You may need to customize:

#### **Required Customizations:**
```yaml
# OpenAI API Key (if using AI features)
- key: OPENAI_API_KEY
  value: your-actual-openai-api-key

# Secret Key for Authentication
- key: SECRET_KEY
  value: your-secure-secret-key
```

#### **Optional Customizations:**
```yaml
# Custom Domain
customDomains:
  - your-domain.com

# Persistent Disk (for data persistence)
disks:
  - name: data-disk
    mountPath: /app/data
    sizeGB: 1
```

### 4. **Deploy**
1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. Monitor the build logs for any issues

## 🔧 Configuration Details

### **Service Configuration**
- **Type**: Web Service
- **Environment**: Docker
- **Plan**: Starter (Free tier)
- **Region**: Oregon (US West)
- **Auto-deploy**: Enabled (deploys on git push)

### **Health Check**
- **Path**: `/_stcore/health`
- **Purpose**: Ensures application is running properly

### **Environment Variables Explained**

#### **Streamlit Settings**
```yaml
STREAMLIT_SERVER_PORT: 8501          # Port for the application
STREAMLIT_SERVER_ADDRESS: 0.0.0.0    # Listen on all interfaces
STREAMLIT_SERVER_HEADLESS: true      # No browser auto-open
STREAMLIT_BROWSER_GATHER_USAGE_STATS: false  # Disable telemetry
```

#### **Application Settings**
```yaml
PYTHONPATH: /app                      # Python module path
PYTHONUNBUFFERED: 1                   # Real-time logging
DATABASE_PATH: /app/data/transactions.db  # Database location
```

#### **File Processing**
```yaml
ENCODINGS_LIST: ["utf-8", "cp1255", "iso-8859-8", "windows-1255"]
DELIMITERS_LIST: [",", ";", "\t"]
MAX_FILE_SIZE_MB: 10
```

#### **Categorization**
```yaml
FUZZY_MATCH_THRESHOLD: 86
KEYWORD_CONFIDENCE: 0.95
FUZZY_CONFIDENCE_THRESHOLD: 0.8
LLM_CONFIDENCE: 0.75
```

## 🛠️ Advanced Configuration

### **Persistent Data Storage**
To ensure data persists across deployments, uncomment the disk configuration:

```yaml
disks:
  - name: data-disk
    mountPath: /app/data
    sizeGB: 1
```

### **Custom Domain**
To use your own domain:

```yaml
customDomains:
  - your-domain.com
```

### **External Database**
For production use, consider using Render's PostgreSQL service:

```yaml
# Add this as a separate service
services:
  - type: pserv
    name: expense-analyzer-db
    plan: starter
    env: postgresql
```

Then update the environment variables:
```yaml
- key: DATABASE_URL
  value: postgresql://user:pass@host:port/dbname
```

## 🔍 Troubleshooting

### **Common Issues**

#### **Build Failures**
- Check Dockerfile syntax
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

#### **Application Won't Start**
- Check environment variables
- Verify port configuration (8501)
- Review application logs in Render dashboard

#### **Database Issues**
- Ensure database path is writable
- Check if persistent disk is configured
- Verify database initialization

#### **File Upload Issues**
- Check `MAX_FILE_SIZE_MB` setting
- Verify file type restrictions
- Ensure proper permissions

### **Logs and Monitoring**
- Access logs via Render dashboard
- Monitor health check endpoint
- Set up alerts for service downtime

## 📊 Performance Optimization

### **Free Tier Limitations**
- **CPU**: 0.1 CPU
- **RAM**: 512 MB
- **Sleep**: Service sleeps after 15 minutes of inactivity
- **Build Time**: 90 minutes per month

### **Upgrade Considerations**
- **Starter Plan**: $7/month for always-on service
- **Standard Plan**: $25/month for better performance
- **Pro Plan**: $85/month for production workloads

## 🔒 Security Considerations

### **Environment Variables**
- Never commit sensitive data to git
- Use Render's environment variable management
- Rotate secrets regularly

### **Authentication**
- Set strong `SECRET_KEY`
- Configure proper session timeouts
- Enable XSRF protection (already configured)

### **File Uploads**
- Validate file types and sizes
- Scan uploaded files for malware
- Implement rate limiting

## 📈 Monitoring and Maintenance

### **Health Monitoring**
- Monitor the `/_stcore/health` endpoint
- Set up uptime monitoring
- Track application performance

### **Regular Maintenance**
- Update dependencies regularly
- Monitor security advisories
- Backup data periodically
- Review and rotate secrets

## 🆘 Support

### **Render Support**
- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)
- [Render Status Page](https://status.render.com)

### **Application Support**
- Check application logs
- Review error messages
- Test locally first
- Use Render's debugging tools

## 🎉 Post-Deployment

After successful deployment:

1. **Test the Application**
   - Access your Render URL
   - Test file uploads
   - Verify authentication
   - Check data persistence

2. **Configure Monitoring**
   - Set up health checks
   - Monitor performance
   - Configure alerts

3. **Documentation**
   - Update README with live URL
   - Document any custom configurations
   - Share deployment details with team

Your Curser Expense Analyzer should now be live and accessible via your Render URL! 🚀
