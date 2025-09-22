import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyBR9KKGW_eed0vc-fMT00VdKTQrrUrF9Bg",
  authDomain: "redditsearchtool.firebaseapp.com",
  projectId: "redditsearchtool",
  storageBucket: "redditsearchtool.firebasestorage.app",
  messagingSenderId: "223812591072",
  appId: "1:223812591072:web:45ddb0fb001173fcea9f85",
  measurementId: "G-30BT54FWR7"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

// Initialize Cloud Firestore and get a reference to the service
export const db = getFirestore(app);

export default app;