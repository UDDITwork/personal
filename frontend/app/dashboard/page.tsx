'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, FileCheck, File, Upload, ArrowRight } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, clearAuth } = useAuthStore();
  const [isHydrated, setIsHydrated] = useState(false);

  // FIXED: Wait for Zustand persist hydration before checking auth
  useEffect(() => {
    // Mark as hydrated after mount
    // Zustand persist middleware hydrates synchronously on mount
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    // Only check auth after hydration completes
    if (isHydrated && !isAuthenticated()) {
      router.push('/login');
    }
  }, [isHydrated, isAuthenticated, router]);

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  // FIXED: Show loading state during hydration
  if (!isHydrated || !isAuthenticated()) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-600">
          {!isHydrated ? 'Loading...' : 'Redirecting to login...'}
        </p>
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

        {/* Upload Document Types */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Documents</CardTitle>
            <CardDescription>
              Select a document type to start extraction
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* IDF Card */}
              <button
                onClick={() => router.push('/upload?type=idf')}
                className="group p-6 rounded-lg border-2 border-blue-200 bg-blue-50 hover:bg-blue-100 hover:border-blue-400 transition-all text-left"
              >
                <FileText className="w-12 h-12 text-blue-600 mb-4" />
                <h3 className="text-xl font-bold text-blue-900 mb-2">IDF Document</h3>
                <p className="text-sm text-blue-700 mb-4">
                  Upload Information Disclosure Form (PDF)
                </p>
                <div className="flex items-center text-blue-600 font-medium group-hover:translate-x-1 transition-transform">
                  <Upload className="w-4 h-4 mr-2" />
                  Upload PDF
                  <ArrowRight className="w-4 h-4 ml-auto" />
                </div>
              </button>

              {/* Transcription Card */}
              <button
                onClick={() => router.push('/upload?type=transcription')}
                className="group p-6 rounded-lg border-2 border-green-200 bg-green-50 hover:bg-green-100 hover:border-green-400 transition-all text-left"
              >
                <FileCheck className="w-12 h-12 text-green-600 mb-4" />
                <h3 className="text-xl font-bold text-green-900 mb-2">Transcription</h3>
                <p className="text-sm text-green-700 mb-4">
                  Upload Interview Transcription (DOCX)
                </p>
                <div className="flex items-center text-green-600 font-medium group-hover:translate-x-1 transition-transform">
                  <Upload className="w-4 h-4 mr-2" />
                  Upload DOCX
                  <ArrowRight className="w-4 h-4 ml-auto" />
                </div>
              </button>

              {/* Claims Card */}
              <button
                onClick={() => router.push('/upload?type=claims')}
                className="group p-6 rounded-lg border-2 border-purple-200 bg-purple-50 hover:bg-purple-100 hover:border-purple-400 transition-all text-left"
              >
                <File className="w-12 h-12 text-purple-600 mb-4" />
                <h3 className="text-xl font-bold text-purple-900 mb-2">Claims</h3>
                <p className="text-sm text-purple-700 mb-4">
                  Upload Patent Claims Document (DOCX)
                </p>
                <div className="flex items-center text-purple-600 font-medium group-hover:translate-x-1 transition-transform">
                  <Upload className="w-4 h-4 mr-2" />
                  Upload DOCX
                  <ArrowRight className="w-4 h-4 ml-auto" />
                </div>
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
