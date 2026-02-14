import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/lib/types';

interface AuthState {
  token: string | null;
  expiresAt: string | null;
  user: User | null;
  _hasHydrated: boolean;
  setAuth: (token: string, expiresAt: string, user: User) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
  isTokenExpired: () => boolean;
  setHasHydrated: (state: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      expiresAt: null,
      user: null,
      _hasHydrated: false,
      setAuth: (token, expiresAt, user) => {
        console.log('[AUTH] setAuth — token length:', token?.length, 'expires:', expiresAt, 'user:', user?.email);
        set({ token, expiresAt, user });
      },
      clearAuth: () => {
        console.log('[AUTH] clearAuth called');
        set({ token: null, expiresAt: null, user: null });
      },
      isAuthenticated: () => {
        const state = get();
        const hasToken = !!state.token;
        const expired = state.isTokenExpired();
        const result = hasToken && !expired;
        if (!result) {
          console.log('[AUTH] isAuthenticated:', result, '— hasToken:', hasToken, 'expired:', expired);
        }
        return result;
      },
      isTokenExpired: () => {
        const expiresAt = get().expiresAt;
        if (!expiresAt) return true;
        // Backend sends naive datetime (no timezone suffix) — treat as UTC
        const utcExpiresAt = expiresAt.endsWith('Z') || expiresAt.includes('+') ? expiresAt : expiresAt + 'Z';
        const expired = new Date(utcExpiresAt) < new Date();
        if (expired) {
          console.log('[AUTH] Token expired — expiresAt:', utcExpiresAt, 'now:', new Date().toISOString());
        }
        return expired;
      },
      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => {
        console.log('[AUTH] Zustand rehydration starting...');
        return (state, error) => {
          if (error) {
            console.error('[AUTH] Zustand rehydration FAILED:', error);
          } else {
            console.log('[AUTH] Zustand rehydration complete — hasToken:', !!state?.token, 'user:', state?.user?.email);
          }
          state?.setHasHydrated(true);
        };
      },
    }
  )
);
