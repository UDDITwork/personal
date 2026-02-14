import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://patmaster-extraction-282996737766.europe-west1.run.app';
console.log('[API] Base URL:', API_URL);

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and check expiration
api.interceptors.request.use((config) => {
  console.log('[API] Request:', config.method?.toUpperCase(), config.url);
  if (typeof window !== 'undefined') {
    const { token, isTokenExpired } = useAuthStore.getState();

    if (token && isTokenExpired()) {
      console.error('[API] Token expired — clearing auth');
      useAuthStore.getState().clearAuth();
      window.location.href = '/login';
      return Promise.reject(new Error('Token expired'));
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API] Response error:', error.response?.status, error.config?.url, error.message);
    if (error.response?.status === 401) {
      // Don't redirect for auth endpoints — 401 on login/register means wrong credentials
      const url = error.config?.url || '';
      if (!url.includes('/auth/')) {
        console.error('[API] 401 on protected endpoint — clearing auth, redirecting');
        if (typeof window !== 'undefined') {
          useAuthStore.getState().clearAuth();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
