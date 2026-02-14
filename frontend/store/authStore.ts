import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/lib/types';

interface AuthState {
  token: string | null;
  expiresAt: string | null;
  user: User | null;
  setAuth: (token: string, expiresAt: string, user: User) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
  isTokenExpired: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      expiresAt: null,
      user: null,
      setAuth: (token, expiresAt, user) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('authToken', token);
          localStorage.setItem('tokenExpiresAt', expiresAt);
        }
        set({ token, expiresAt, user });
      },
      clearAuth: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('authToken');
          localStorage.removeItem('tokenExpiresAt');
        }
        set({ token: null, expiresAt: null, user: null });
      },
      isAuthenticated: () => {
        const state = get();
        return !!state.token && !state.isTokenExpired();
      },
      isTokenExpired: () => {
        const expiresAt = get().expiresAt;
        if (!expiresAt) return true;
        // FIXED: Token is valid until expiration time (< not <=)
        return new Date(expiresAt) < new Date();
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
