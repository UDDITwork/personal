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
  if (typeof window !== 'undefined') {
    const { token, isTokenExpired } = useAuthStore.getState();

    if (token && isTokenExpired()) {
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
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
