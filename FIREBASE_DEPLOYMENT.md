# Firebase Deployment Guide

This project is now configured to deploy both frontend and backend using Firebase!

## 🔥 Firebase Setup

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project"
3. Name it: `reddit-search-tool` (or update `.firebaserc` if different)
4. Enable Google Analytics (optional)
5. Wait for project creation

### 2. Enable Required Services

In your Firebase project console:

1. **Functions**: Go to Functions → Get started → Follow setup
2. **Hosting**: Go to Hosting → Get started → Follow setup
3. **Authentication** (optional): For API key protection later

### 3. Install Firebase CLI

```bash
npm install -g firebase-tools
```

### 4. Login and Initialize

```bash
# Login to Firebase
firebase login

# Initialize project (in project root)
firebase init

# Select:
# - Functions (already configured)
# - Hosting (already configured)
# - Use existing project: reddit-search-tool
```

## 🚀 Deployment Options

### Option 1: Firebase Hosting + Functions (Recommended)

**Complete full-stack hosting on Firebase:**

```bash
# Build the frontend
npm run build

# Deploy everything
firebase deploy

# Or deploy separately:
firebase deploy --only hosting  # Frontend only
firebase deploy --only functions  # Backend only
```

**Benefits:**
- ✅ Same domain for frontend/backend (no CORS issues)
- ✅ Automatic HTTPS
- ✅ CDN for frontend
- ✅ Serverless backend scaling
- ✅ Firebase's generous free tier

### Option 2: GitHub Pages + Firebase Functions

**Frontend on GitHub Pages, backend on Firebase:**

```bash
# Deploy backend to Firebase
firebase deploy --only functions

# Frontend deploys automatically via GitHub Actions
git push origin main
```

**Configuration needed:**
- Update `src/api.ts` with your Firebase Functions URL
- Set GitHub repository secrets for CI/CD

## 🔧 Environment Variables

### Local Development

Create `.env` file:
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
```

### Firebase Functions

Set environment variables:
```bash
# Set secrets for Firebase Functions
firebase functions:config:set anthropic.api_key="your_anthropic_api_key"
firebase functions:config:set reddit.client_id="your_reddit_client_id"
firebase functions:config:set reddit.client_secret="your_reddit_client_secret"
firebase functions:config:set reddit.user_agent="your_reddit_user_agent"

# Deploy with new config
firebase deploy --only functions
```

### GitHub Actions (for Option 2)

Add to GitHub repository secrets:
- `FIREBASE_TOKEN`: Get with `firebase login:ci`

## 📁 Project Structure

```
project/
├── src/                    # React frontend
├── functions/              # Firebase Functions (Python)
│   ├── main.py            # Flask app entry point
│   ├── requirements.txt   # Python dependencies
│   └── package.json       # Node.js config for Functions
├── firebase.json          # Firebase configuration
├── .firebaserc           # Firebase project settings
└── .github/workflows/    # CI/CD configuration
```

## 🔄 Local Development

### Option A: Full Firebase Emulation
```bash
# Start Firebase emulators
firebase emulators:start

# In another terminal, start frontend
npm run dev
```

### Option B: Original Flask Server
```bash
# Start original Flask server
npm run dev  # Runs both frontend and Flask backend
```

## 📊 Cost Considerations

**Firebase Free Tier includes:**
- Functions: 2M invocations/month
- Hosting: 10GB storage + 360MB/day transfer
- Firestore: 1GB storage + 50k reads/day

**Estimated monthly costs for moderate usage:**
- Firebase: $0-5 (likely free tier)
- Anthropic API: Variable based on usage
- GitHub Pages: Free

## 🛠️ Troubleshooting

### Common Issues:

1. **Functions deployment fails**
   ```bash
   cd functions
   pip install -r requirements.txt  # Test locally first
   ```

2. **CORS errors**
   - Use Option 1 (Firebase Hosting) for same-domain deployment
   - Or configure CORS in `functions/main.py`

3. **Environment variables not working**
   ```bash
   firebase functions:config:get  # Check current config
   ```

4. **Build errors**
   ```bash
   npm run build  # Test build locally
   ```

### Firebase CLI cannot find Python Functions SDK

If you see errors like:

```
Error: Failed to find location of Firebase Functions SDK. Did you forget to run '. "functions/venv/bin/activate" && python3.12 -m pip install -r requirements.txt'?
```

Fix steps that worked:

1) Ensure the Firebase Functions SDK for Python is installed:
```bash
cd functions
python3.12 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```
Add this to `functions/requirements.txt` if missing:
```
firebase-functions==0.4.2
```

2) On Apple Silicon, align architectures to avoid cffi/cryptography errors. Since Node/Firebase CLI may be x86_64:
```bash
cd functions
rm -rf venv
arch -x86_64 python3.12 -m venv venv
source venv/bin/activate
arch -x86_64 pip install --no-cache-dir -r requirements.txt
```

Then redeploy from project root:
```bash
firebase deploy --only functions
```

## 🚦 Next Steps

1. **Create Firebase project** and update `.firebaserc`
2. **Set environment variables** in Firebase Functions config
3. **Deploy to Firebase**: `firebase deploy`
4. **Test the deployed app** at your Firebase Hosting URL
5. **Configure custom domain** (optional)

Your app will be available at:
- `https://reddit-search-tool.web.app`
- `https://reddit-search-tool.firebaseapp.com`

## 🎯 Benefits of Firebase Deployment

- **Serverless**: No server management
- **Scalable**: Auto-scales with usage
- **Fast**: Global CDN for frontend
- **Secure**: HTTPS by default
- **Cost-effective**: Pay only for usage
- **Integrated**: Functions + Hosting work seamlessly together