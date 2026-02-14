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
        console.log('[AUTH] setAuth called', { tokenLength: token?.length, expiresAt, userEmail: user?.email });
        set({ token, expiresAt, user });
        console.log('[AUTH] setAuth complete — store updated');
      },
      clearAuth: () => {
        console.log('[AUTH] clearAuth called — clearing token, user, expiresAt');
        set({ token: null, expiresAt: null, user: null });
      },
      isAuthenticated: () => {
        const state = get();
        const hasToken = !!state.token;
        const expired = state.isTokenExpired();
        const result = hasToken && !expired;
        console.log('[AUTH] isAuthenticated()', { hasToken, expired, result });
        return result;
      },
      isTokenExpired: () => {
        const expiresAt = get().expiresAt;
        if (!expiresAt) return true;
        // Backend sends naive datetime (no timezone suffix) — treat as UTC
        const utcExpiresAt = expiresAt.endsWith('Z') || expiresAt.includes('+') ? expiresAt : expiresAt + 'Z';
        const expired = new Date(utcExpiresAt) < new Date();
        console.log('[AUTH] isTokenExpired()', { expiresAt, utcExpiresAt, now: new Date().toISOString(), expired });
        return expired;
      },
      setHasHydrated: (state) => {
        console.log('[AUTH] setHasHydrated:', state);
        set({ _hasHydrated: state });
      },
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => {
        console.log('[AUTH] Zustand rehydration STARTING from localStorage...');
        return (state, error) => {
          if (error) {
            console.error('[AUTH] Zustand rehydration FAILED:', error);
          } else {
            console.log('[AUTH] Zustand rehydration COMPLETE', {
              hasToken: !!state?.token,
              hasUser: !!state?.user,
              expiresAt: state?.expiresAt,
            });
          }
          state?.setHasHydrated(true);
        };
      },
    }
  )
);
