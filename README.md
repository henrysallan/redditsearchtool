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

This project is configured for automatic deployment to GitHub Pages using GitHub Actions.

### Automatic Deployment
- Every push to `main` or `master` branch triggers automatic deployment
- GitHub Actions builds and deploys the React frontend
- Live site: `https://henrysallan.github.io/redditsearchtool`

### Setup GitHub Pages
1. Go to repository Settings > Pages
2. Set source to "GitHub Actions"
3. The workflow will handle the rest automatically

⚠️ **Note**: Only the React frontend is deployed to GitHub Pages. The Flask backend requires a separate hosting service.

For full deployment documentation, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## How It Works

-   **Frontend**: A React application built with Vite that provides a search bar for user queries.
-   **Backend**: A Flask server that exposes a `/api/search-summarize` endpoint.
-   **Reddit Integration**: Uses the PRAW library to search for posts on Reddit based on the user's query.
-   **Summarization**: The collected text is sent to the Anthropic Claude API for summarization.
-   **Display**: The final summary is sent back to the frontend and rendered as markdown.
