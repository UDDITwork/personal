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
        set({ token, expiresAt, user });
      },
      clearAuth: () => {
        set({ token: null, expiresAt: null, user: null });
      },
      isAuthenticated: () => {
        const state = get();
        return !!state.token && !state.isTokenExpired();
      },
      isTokenExpired: () => {
        const expiresAt = get().expiresAt;
        if (!expiresAt) return true;
        return new Date(expiresAt) < new Date();
      },
      setHasHydrated: (state) => {
        set({ _hasHydrated: state });
      },
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => {
        return (state) => {
          state?.setHasHydrated(true);
        };
      },
    }
  )
);
