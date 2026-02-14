'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, _hasHydrated } = useAuthStore();

  useEffect(() => {
    if (!_hasHydrated) return;
    if (isAuthenticated()) {
      router.push('/dashboard');
    } else {
      router.push('/login');
    }
  }, [_hasHydrated, isAuthenticated, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-slate-600">Redirecting...</p>
    </div>
  );
}
