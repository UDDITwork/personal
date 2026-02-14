'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, _hasHydrated } = useAuthStore();

  console.log('[AUTH][HOME] Render — _hasHydrated:', _hasHydrated);

  useEffect(() => {
    console.log('[AUTH][HOME] useEffect — _hasHydrated:', _hasHydrated);
    if (!_hasHydrated) return;
    const authed = isAuthenticated();
    console.log('[AUTH][HOME] Hydrated, isAuthenticated:', authed);
    if (authed) {
      console.log('[AUTH][HOME] Redirecting to /dashboard');
      router.push('/dashboard');
    } else {
      console.log('[AUTH][HOME] Redirecting to /login');
      router.push('/login');
    }
  }, [_hasHydrated, isAuthenticated, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-slate-600">Redirecting...</p>
    </div>
  );
}
