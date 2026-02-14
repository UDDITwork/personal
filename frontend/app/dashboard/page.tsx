'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, clearAuth } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  if (!isAuthenticated()) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-600">Redirecting to login...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-slate-600 mt-1">
              Welcome back, {user?.full_name || user?.email}!
            </p>
          </div>
          <Button variant="outline" onClick={handleLogout}>
            Logout
          </Button>
        </div>

        {/* Welcome Card */}
        <Card>
          <CardHeader>
            <CardTitle>PATMASTER Document Extraction</CardTitle>
            <CardDescription>
              Your document extraction platform is ready to use
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h3 className="font-semibold text-blue-900">Projects</h3>
                  <p className="text-2xl font-bold text-blue-700 mt-2">0</p>
                  <p className="text-sm text-blue-600 mt-1">Total projects</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h3 className="font-semibold text-green-900">Documents</h3>
                  <p className="text-2xl font-bold text-green-700 mt-2">0</p>
                  <p className="text-sm text-green-600 mt-1">Processed documents</p>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h3 className="font-semibold text-purple-900">Extractions</h3>
                  <p className="text-2xl font-bold text-purple-700 mt-2">0</p>
                  <p className="text-sm text-purple-600 mt-1">Completed extractions</p>
                </div>
              </div>

              <div className="pt-4 border-t">
                <h3 className="font-semibold text-slate-900 mb-3">Coming Soon</h3>
                <ul className="space-y-2 text-sm text-slate-600">
                  <li>✅ Authentication & User Management</li>
                  <li>🔄 Project Creation & Management (In Progress)</li>
                  <li>⏳ Document Upload Interface</li>
                  <li>⏳ Extraction Results Viewer</li>
                  <li>⏳ Real-time Processing Status</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* User Info Card */}
        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-600">Email:</span>
                <span className="font-medium">{user?.email}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Full Name:</span>
                <span className="font-medium">{user?.full_name || 'Not set'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Account Status:</span>
                <span className="font-medium text-green-600">
                  {user?.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Member Since:</span>
                <span className="font-medium">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
