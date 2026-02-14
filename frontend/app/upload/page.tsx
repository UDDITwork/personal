'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Upload, FileText, FileCheck, File } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

type DocumentType = 'idf' | 'transcription' | 'claims';

interface UploadResponse {
  success: boolean;
  message: string;
  document_id: string;
  project_id: string;
  document_type: string;
  file_name: string;
  processing_status: string;
}

function UploadPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, _hasHydrated } = useAuthStore();

  const typeParam = searchParams.get('type') as DocumentType | null;
  const [selectedType, setSelectedType] = useState<DocumentType | null>(typeParam);
  const [file, setFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  console.log('[AUTH][UPLOAD] Render — _hasHydrated:', _hasHydrated);

  useEffect(() => {
    console.log('[AUTH][UPLOAD] useEffect — _hasHydrated:', _hasHydrated);
    if (_hasHydrated) {
      const authed = isAuthenticated();
      console.log('[AUTH][UPLOAD] Hydrated, isAuthenticated:', authed);
      if (!authed) {
        console.log('[AUTH][UPLOAD] NOT authenticated — redirecting to /login');
        router.push('/login');
      }
    }
  }, [_hasHydrated, isAuthenticated, router]);

  const documentTypes = {
    idf: {
      title: 'IDF Document',
      description: 'Information Disclosure Form',
      icon: FileText,
      color: 'blue',
      accept: '.pdf',
      fileType: 'PDF'
    },
    transcription: {
      title: 'Transcription',
      description: 'Interview Transcription',
      icon: FileCheck,
      color: 'green',
      accept: '.docx',
      fileType: 'DOCX'
    },
    claims: {
      title: 'Claims',
      description: 'Patent Claims',
      icon: File,
      color: 'purple',
      accept: '.docx',
      fileType: 'DOCX'
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];

      if (!selectedType) {
        toast.error('Please select a document type first');
        return;
      }

      const acceptedType = documentTypes[selectedType].accept;
      const fileExt = '.' + selectedFile.name.split('.').pop();

      if (fileExt.toLowerCase() !== acceptedType.toLowerCase()) {
        toast.error(`Only ${documentTypes[selectedType].fileType} files are allowed for ${selectedType.toUpperCase()}`);
        return;
      }

      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file || !selectedType || !projectName.trim()) {
      toast.error('Please fill all fields');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      // Step 1: Create project
      toast.info('Creating project...');
      const projectResponse = await api.post('/projects/', {
        name: projectName,
        description: `${selectedType.toUpperCase()} document upload`
      });

      const projectId = projectResponse.data.id;
      setUploadProgress(30);

      // Step 2: Upload document
      toast.info('Uploading document...');
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await api.post<UploadResponse>(
        `/projects/${projectId}/upload/${selectedType}`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const progress = 30 + Math.round((progressEvent.loaded * 70) / progressEvent.total);
              setUploadProgress(progress);
            }
          }
        }
      );

      setUploadProgress(100);
      toast.success('Document uploaded successfully! Starting extraction...');

      // Redirect to results page
      setTimeout(() => {
        router.push(`/results/${uploadResponse.data.document_id}?project=${projectId}`);
      }, 1000);

    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  if (!_hasHydrated || !isAuthenticated()) {
    console.log('[AUTH][UPLOAD] Guard — not ready, returning null. _hasHydrated:', _hasHydrated);
    return null;
  }
  console.log('[AUTH][UPLOAD] Rendering upload page');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Upload Document</h1>
          <p className="text-slate-600 mt-1">
            Select document type and upload your file for extraction
          </p>
        </div>

        {/* Step 1: Select Document Type */}
        <Card>
          <CardHeader>
            <CardTitle>1. Select Document Type</CardTitle>
            <CardDescription>Choose the type of document you want to upload</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(Object.keys(documentTypes) as DocumentType[]).map((type) => {
                const docType = documentTypes[type];
                const Icon = docType.icon;
                const isSelected = selectedType === type;

                return (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
                    disabled={uploading}
                    className={`
                      p-6 rounded-lg border-2 transition-all text-left
                      ${isSelected
                        ? `border-${docType.color}-500 bg-${docType.color}-50`
                        : 'border-slate-200 hover:border-slate-300'
                      }
                      ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    <Icon className={`w-8 h-8 mb-3 ${isSelected ? `text-${docType.color}-600` : 'text-slate-400'}`} />
                    <h3 className="font-semibold text-slate-900">{docType.title}</h3>
                    <p className="text-sm text-slate-600 mt-1">{docType.description}</p>
                    <p className="text-xs text-slate-500 mt-2">({docType.fileType} only)</p>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Project Name */}
        {selectedType && (
          <Card>
            <CardHeader>
              <CardTitle>2. Project Name</CardTitle>
              <CardDescription>Give your project a name for easy identification</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="projectName">Project Name</Label>
                <Input
                  id="projectName"
                  type="text"
                  placeholder="e.g., Patent Application Q1 2024"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  disabled={uploading}
                />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Upload File */}
        {selectedType && projectName && (
          <Card>
            <CardHeader>
              <CardTitle>3. Upload File</CardTitle>
              <CardDescription>
                Select a {documentTypes[selectedType].fileType} file to upload
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="file">
                  File ({documentTypes[selectedType].fileType} only)
                </Label>
                <Input
                  id="file"
                  type="file"
                  accept={documentTypes[selectedType].accept}
                  onChange={handleFileChange}
                  disabled={uploading}
                />
                {file && (
                  <p className="text-sm text-slate-600">
                    Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </p>
                )}
              </div>

              {uploading && (
                <div className="space-y-2">
                  <Progress value={uploadProgress} />
                  <p className="text-sm text-slate-600 text-center">
                    {uploadProgress < 30 ? 'Creating project...' :
                     uploadProgress < 100 ? 'Uploading document...' : 'Processing...'}
                  </p>
                </div>
              )}

              <Button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="w-full"
                size="lg"
              >
                <Upload className="w-4 h-4 mr-2" />
                {uploading ? 'Uploading...' : 'Upload & Process'}
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <UploadPageContent />
    </Suspense>
  );
}
