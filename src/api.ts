// API configuration for both local development and Firebase Functions

const getApiBaseUrl = (): string => {
  // If we're in development (localhost), use the local server
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:5001'
  }
  
  // If deployed on Firebase Hosting, API calls go to the same domain (Firebase will route to Functions)
  if (window.location.hostname.includes('.web.app') || window.location.hostname.includes('.firebaseapp.com')) {
    return '' // Use relative URLs for Firebase Hosting
  }
  
  // If deployed on GitHub Pages, use Firebase Functions directly
  // Use the deployed Cloud Functions URL with the function name appended
  // Note: Project ID is 'redditsearchtool' (no hyphens)
  return 'https://us-central1-redditsearchtool.cloudfunctions.net/api'
}

export const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const baseUrl = getApiBaseUrl()
  // Avoid double '/api' when baseUrl already ends with '/api' and endpoint starts with '/api/'
  const normalizedEndpoint = baseUrl.endsWith('/api') && endpoint.startsWith('/api/')
    ? endpoint.slice(4)
    : endpoint
  const url = baseUrl ? `${baseUrl}${normalizedEndpoint}` : normalizedEndpoint
  
  // Add default headers
  const defaultHeaders = {
    'Content-Type': 'application/json',
    ...options.headers
  }
  
  return fetch(url, {
    ...options,
    headers: defaultHeaders
  })
}

export default apiCall