import { initializeApp } from 'firebase/app'
import { getAnalytics } from 'firebase/analytics'

const firebaseConfig = {
  apiKey: 'AIzaSyCIQNnEeOJIeVrERxplV0MkVR-lIn1ZTg8',
  authDomain: 'land-scanner-tamil-developers.firebaseapp.com',
  projectId: 'land-scanner-tamil-developers',
  storageBucket: 'land-scanner-tamil-developers.firebasestorage.app',
  messagingSenderId: '794666957594',
  appId: '1:794666957594:web:d32a92dd1cbb51ac834aa3',
  measurementId: 'G-5B5J2SXY5H'
}

// Initialize Firebase
let app = null
let analytics = null

try {
  app = initializeApp(firebaseConfig)
  analytics = getAnalytics(app)
  console.log('Firebase initialized successfully')
} catch (error) {
  console.error('Firebase initialization error:', error)
}

export { app, analytics }
