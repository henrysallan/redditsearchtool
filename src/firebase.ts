import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyBl_YtWCxYKJRzgYKgXKvLlgJXjcOhwP9Y",
  authDomain: "redditsearchtool.firebaseapp.com",
  projectId: "redditsearchtool",
  storageBucket: "redditsearchtool.firebasestorage.app",
  messagingSenderId: "747823491710",
  appId: "1:747823491710:web:1f3ebcac4b1b58d3b8c4f8"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

// Initialize Cloud Firestore and get a reference to the service
export const db = getFirestore(app);

export default app;