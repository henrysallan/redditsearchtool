# Deployment Guide

## GitHub Actions + GitHub Pages Deployment

This project uses GitHub Actions for automated CI/CD deployment to GitHub Pages.

### Setup

1. **GitHub Repository Setup**
   - Ensure your repository is public or you have GitHub Pro for private repo GitHub Pages
   - Repository should be named `redditsearchtool` (or update the homepage in package.json)

2. **GitHub Pages Settings**
   - Go to your repository settings on GitHub
   - Navigate to "Pages" section  
   - Set source to "GitHub Actions"
   - Save the settings

3. **Automatic Deployment**
   - Every push to `main` or `master` branch automatically triggers deployment
   - GitHub Actions workflow builds and deploys the app
   - No manual commands needed!

### GitHub Actions Workflow

The workflow (`.github/workflows/deploy.yml`) automatically:
1. Checks out the code
2. Sets up Node.js environment
3. Installs dependencies with `npm ci`
4. Builds the React app with `npm run build`
5. Deploys to GitHub Pages

### Manual Deployment (Alternative)

If you prefer manual deployment:
```bash
# Build and deploy to GitHub Pages
npm run deploy

# Or run the individual steps:
npm run predeploy  # Builds the project
npm run deploy     # Deploys to gh-pages branch
```

### Important Notes

⚠️ **Backend Limitations**: GitHub Pages only serves static files. The Flask backend (`server/app.py`) will not work on GitHub Pages. The deployed version will only show the frontend interface.

### Alternative Deployment Options

For full-stack deployment with backend support, consider:

1. **Netlify + Backend Service**
   - Deploy frontend to Netlify
   - Deploy backend to Railway, Render, or Heroku

2. **Vercel**
   - Can handle both frontend and serverless functions
   - Would require converting Flask routes to Vercel serverless functions

3. **Railway/Render**
   - Full-stack deployment with both frontend and backend
   - Docker-based deployment

### Local Development

To run the full application locally:
```bash
npm run dev  # Runs both frontend (Vite) and backend (Flask)
```

### Configuration

- **Homepage**: Set in `package.json` - update if repository name changes
- **Base Path**: Configured in `vite.config.ts` for GitHub Pages routing
- **Build Output**: Set to `dist` folder for GitHub Pages compatibility