import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://patmaster-extraction-282996737766.europe-west1.run.app';

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and check expiration
api.interceptors.request.use((config) => {
  console.log('[AUTH][API] Request interceptor —', config.method?.toUpperCase(), config.url);
  if (typeof window !== 'undefined') {
    const { token, isTokenExpired } = useAuthStore.getState();
    console.log('[AUTH][API] Token present:', !!token);

    if (token && isTokenExpired()) {
      console.log('[AUTH][API] Token EXPIRED — clearing auth, redirecting to /login');
      useAuthStore.getState().clearAuth();
      window.location.href = '/login';
      return Promise.reject(new Error('Token expired'));
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('[AUTH][API] Authorization header set');
    } else {
      console.log('[AUTH][API] No token — request sent without auth header');
    }
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log('[AUTH][API] Response OK:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('[AUTH][API] Response ERROR:', error.response?.status, error.config?.url, error.response?.data);
    if (error.response?.status === 401) {
      console.log('[AUTH][API] 401 Unauthorized — clearing auth, redirecting to /login');
      if (typeof window !== 'undefined') {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
