# Reddit Summarizer (Vite + Flask + PRAW)

This project allows you to enter a search query, which is then used to find the top 3 posts on Reddit. The text from these posts and their comments is collected and summarized using the Anthropic Claude API. The summary is then displayed in a beautifully formatted way on the web page.

## Setup

### 1. Environment Variables

You'll need to set up your API keys for Reddit and Anthropic. Copy the example environment file:

```zsh
cp .env.example .env
```

Then, edit the `.env` file with your credentials. You'll need to add your Reddit `client_id`, `client_secret`, and `user_agent`, as well as your `ANTHROPIC_API_KEY`.

```
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 2. Install Dependencies

**Frontend (Node.js):**

```zsh
npm install
```

**Backend (Python):**

First, make sure you have a Python virtual environment set up and activated. Then, install the required packages:

```zsh
pip install -r server/requirements.txt
```

## Development

To run the development servers for both the frontend and backend, use the following command:

```zsh
npm run dev
```

This will start the Vite frontend on `http://localhost:5173` and the Flask backend on `http://localhost:5001`.

## Deployment

We deploy the entire app with Firebase (Hosting + Functions). Push to `main` and GitHub Actions will build and deploy to Firebase Hosting, with `/api/**` routed to your Cloud Function.

```bash
# One-time setup
firebase functions:secrets:set ANTHROPIC_API_KEY
firebase functions:secrets:set REDDIT_CLIENT_ID
firebase functions:secrets:set REDDIT_CLIENT_SECRET
firebase functions:secrets:set REDDIT_USER_AGENT

# Manual deploy (optional; CI runs on push)
npm run build && firebase deploy
```

Docs: [FIREBASE_DEPLOYMENT.md](./FIREBASE_DEPLOYMENT.md)

## How It Works

-   **Frontend**: A React application built with Vite that provides a search bar for user queries.
-   **Backend**: A Flask server that exposes a `/api/search-summarize` endpoint.
-   **Reddit Integration**: Uses the PRAW library to search for posts on Reddit based on the user's query.
-   **Summarization**: The collected text is sent to the Anthropic Claude API for summarization.
-   **Display**: The final summary is sent back to the frontend and rendered as markdown.
