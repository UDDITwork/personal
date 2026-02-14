'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, FileCheck, File, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

type DocumentType = 'idf' | 'transcription' | 'claims';

interface UploadStatus {
  file: File | null;
  uploading: boolean;
  progress: number;
  documentId: string | null;
  status: 'idle' | 'uploading' | 'done' | 'error';
  error: string | null;
}

const documentTypes: Record<DocumentType, {
  title: string;
  description: string;
  icon: typeof FileText;
  color: string;
  accept: string;
  fileType: string;
}> = {
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

function UploadPageContent() {
  console.log('%c[UPLOAD PAGE] Component rendered', 'color:#E91E63;font-weight:bold');
  const router = useRouter();
  const { isAuthenticated, _hasHydrated } = useAuthStore();

  const [projectName, setProjectName] = useState('');
  const [projectId, setProjectId] = useState<string | null>(null);
  const [creatingProject, setCreatingProject] = useState(false);

  const [uploads, setUploads] = useState<Record<DocumentType, UploadStatus>>({
    idf: { file: null, uploading: false, progress: 0, documentId: null, status: 'idle', error: null },
    transcription: { file: null, uploading: false, progress: 0, documentId: null, status: 'idle', error: null },
    claims: { file: null, uploading: false, progress: 0, documentId: null, status: 'idle', error: null },
  });

  useEffect(() => {
    console.log('%c[UPLOAD PAGE] useEffect — auth guard', 'color:#9C27B0;font-weight:bold', {
      _hasHydrated,
      isAuth: _hasHydrated ? isAuthenticated() : 'waiting',
    });

    if (_hasHydrated && !isAuthenticated()) {
      console.log('%c[UPLOAD PAGE] ▶ NOT authenticated — redirecting to /login', 'color:#f44336;font-weight:bold');
      router.push('/login');
    }
  }, [_hasHydrated, isAuthenticated, router]);

  const handleCreateProject = async () => {
    if (!projectName.trim()) {
      console.log('%c[UPLOAD PAGE] ✗ Project name empty — aborting', 'color:#FF9800');
      toast.error('Please enter a project name');
      return;
    }

    console.log('%c[UPLOAD PAGE] ▶ "Create Project" clicked', 'color:#2196F3;font-weight:bold', {
      projectName: projectName.trim(),
    });

    setCreatingProject(true);
    try {
      console.log('%c[UPLOAD PAGE] ▶ Calling POST /projects/', 'color:#2196F3;font-weight:bold', {
        endpoint: '/projects/',
        payload: { name: projectName, description: 'Patent extraction project' },
      });

      const response = await api.post('/projects/', {
        name: projectName,
        description: 'Patent extraction project'
      });

      console.log('%c[UPLOAD PAGE] ✓ Project created', 'color:#4CAF50;font-weight:bold', {
        projectId: response.data.id,
        projectName: response.data.name,
        fullResponse: response.data,
      });

      setProjectId(response.data.id);
      toast.success('Project created!');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string }; status?: number }; message?: string };
      console.error('%c[UPLOAD PAGE] ✗ Project creation FAILED', 'color:#f44336;font-weight:bold', {
        status: err.response?.status,
        detail: err.response?.data?.detail,
        message: err.message,
      });
      toast.error(err.response?.data?.detail || 'Failed to create project');
    } finally {
      setCreatingProject(false);
    }
  };

  const handleFileSelect = (type: DocumentType, e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const acceptedType = documentTypes[type].accept;
      const fileExt = '.' + selectedFile.name.split('.').pop();

      console.log('%c[UPLOAD PAGE] ▶ File selected', 'color:#2196F3;font-weight:bold', {
        type,
        fileName: selectedFile.name,
        fileSize: `${(selectedFile.size / 1024).toFixed(1)} KB`,
        fileType: selectedFile.type,
        extension: fileExt,
        acceptedType,
      });

      if (fileExt.toLowerCase() !== acceptedType.toLowerCase()) {
        console.error('%c[UPLOAD PAGE] ✗ File type mismatch', 'color:#f44336;font-weight:bold', {
          expected: acceptedType,
          got: fileExt,
        });
        toast.error(`Only ${documentTypes[type].fileType} files are allowed for ${type.toUpperCase()}`);
        return;
      }

      setUploads(prev => ({
        ...prev,
        [type]: { ...prev[type], file: selectedFile, status: 'idle', error: null, documentId: null }
      }));
      console.log('%c[UPLOAD PAGE] ✓ File set for upload slot', 'color:#4CAF50', { type, fileName: selectedFile.name });
    }
  };

  const handleUploadFile = async (type: DocumentType) => {
    const upload = uploads[type];
    if (!upload.file || !projectId) {
      console.log('%c[UPLOAD PAGE] ✗ Upload aborted — missing file or projectId', 'color:#FF9800', { hasFile: !!upload.file, projectId });
      return;
    }

    console.log('%c[UPLOAD PAGE] ▶ Upload button clicked', 'color:#2196F3;font-weight:bold', {
      type,
      fileName: upload.file.name,
      fileSize: `${(upload.file.size / 1024).toFixed(1)} KB`,
      projectId,
      endpoint: `/projects/${projectId}/upload/${type}`,
    });

    setUploads(prev => ({
      ...prev,
      [type]: { ...prev[type], uploading: true, progress: 0, status: 'uploading', error: null }
    }));

    try {
      const formData = new FormData();
      formData.append('file', upload.file);

      console.log('%c[UPLOAD PAGE] ▶ Calling POST /projects/%s/upload/%s', 'color:#2196F3;font-weight:bold', projectId, type);

      const response = await api.post(
        `/projects/${projectId}/upload/${type}`,
        formData,
        {
          headers: { 'Content-Type': undefined },  // Let browser set multipart boundary automatically
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              console.log('%c[UPLOAD PAGE] ⬆ Upload progress', 'color:#9E9E9E', { type, progress: `${progress}%`, loaded: progressEvent.loaded, total: progressEvent.total });
              setUploads(prev => ({
                ...prev,
                [type]: { ...prev[type], progress }
              }));
            }
          }
        }
      );

      console.log('%c[UPLOAD PAGE] ✓ Upload SUCCESS', 'color:#4CAF50;font-weight:bold', {
        type,
        documentId: response.data.document_id,
        status: response.status,
        fullResponse: response.data,
      });

      setUploads(prev => ({
        ...prev,
        [type]: { ...prev[type], uploading: false, progress: 100, status: 'done', documentId: response.data.document_id }
      }));
      toast.success(`${documentTypes[type].title} uploaded!`);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string }; status?: number }; message?: string };
      console.error('%c[UPLOAD PAGE] ✗ Upload FAILED', 'color:#f44336;font-weight:bold', {
        type,
        status: err.response?.status,
        detail: err.response?.data?.detail,
        message: err.message,
        fullError: err.response?.data,
      });
      setUploads(prev => ({
        ...prev,
        [type]: { ...prev[type], uploading: false, progress: 0, status: 'error', error: err.response?.data?.detail || 'Upload failed' }
      }));
      toast.error(err.response?.data?.detail || `${documentTypes[type].title} upload failed`);
    }
  };

  const handleViewResults = () => {
    const firstDone = Object.entries(uploads).find(([, u]) => u.status === 'done');
    if (firstDone) {
      console.log('%c[UPLOAD PAGE] ▶ "View Results" clicked — navigating', 'color:#2196F3;font-weight:bold', {
        documentId: firstDone[1].documentId,
        projectId,
        allUploads: Object.fromEntries(
          Object.entries(uploads).map(([k, v]) => [k, { status: v.status, documentId: v.documentId }])
        ),
      });
      router.push(`/results/${firstDone[1].documentId}?project=${projectId}`);
    }
  };

  const handleBackToDashboard = () => {
    console.log('%c[UPLOAD PAGE] ▶ "Back to Dashboard" clicked', 'color:#2196F3;font-weight:bold');
    router.push('/dashboard');
  };

  const completedCount = Object.values(uploads).filter(u => u.status === 'done').length;

  if (!_hasHydrated || !isAuthenticated()) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">New Project</h1>
          <p className="text-slate-600 mt-1">
            Create a project and upload your documents for extraction
          </p>
        </div>

        {/* Step 1: Project Name */}
        <Card>
          <CardHeader>
            <CardTitle>1. Create Project</CardTitle>
            <CardDescription>Give your project a name to get started</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <Input
                type="text"
                placeholder="e.g., Patent Application Q1 2024"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                disabled={!!projectId || creatingProject}
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !projectId) handleCreateProject();
                }}
              />
              {!projectId ? (
                <Button onClick={handleCreateProject} disabled={!projectName.trim() || creatingProject}>
                  {creatingProject ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create'
                  )}
                </Button>
              ) : (
                <div className="flex items-center text-green-600 px-3">
                  <CheckCircle2 className="w-5 h-5 mr-2" />
                  Created
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Upload Documents */}
        {projectId && (
          <Card>
            <CardHeader>
              <CardTitle>2. Upload Documents</CardTitle>
              <CardDescription>
                Upload your documents into this project ({completedCount}/3 uploaded)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {(Object.keys(documentTypes) as DocumentType[]).map((type) => {
                  const docType = documentTypes[type];
                  const upload = uploads[type];
                  const Icon = docType.icon;

                  return (
                    <div
                      key={type}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        upload.status === 'done'
                          ? 'border-green-300 bg-green-50'
                          : upload.status === 'error'
                          ? 'border-red-300 bg-red-50'
                          : 'border-slate-200 bg-white'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <Icon className={`w-8 h-8 flex-shrink-0 ${
                          upload.status === 'done' ? 'text-green-600' :
                          upload.status === 'error' ? 'text-red-600' :
                          `text-${docType.color}-600`
                        }`} />
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-slate-900">{docType.title}</h3>
                          <p className="text-sm text-slate-500">{docType.description} ({docType.fileType} only)</p>

                          {upload.status === 'done' && (
                            <p className="text-sm text-green-600 mt-1 flex items-center">
                              <CheckCircle2 className="w-4 h-4 mr-1" />
                              Uploaded successfully
                            </p>
                          )}
                          {upload.status === 'error' && (
                            <p className="text-sm text-red-600 mt-1 flex items-center">
                              <AlertCircle className="w-4 h-4 mr-1" />
                              {upload.error}
                            </p>
                          )}
                          {upload.uploading && (
                            <Progress value={upload.progress} className="mt-2 h-2" />
                          )}
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {upload.status !== 'done' && (
                            <>
                              <Input
                                type="file"
                                accept={docType.accept}
                                onChange={(e) => handleFileSelect(type, e)}
                                disabled={upload.uploading}
                                className="w-48"
                              />
                              {upload.file && !upload.uploading && (
                                <Button
                                  size="sm"
                                  onClick={() => handleUploadFile(type)}
                                >
                                  <Upload className="w-4 h-4 mr-1" />
                                  Upload
                                </Button>
                              )}
                              {upload.uploading && (
                                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: View Results */}
        {projectId && completedCount > 0 && (
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={handleBackToDashboard}
            >
              Back to Dashboard
            </Button>
            {completedCount > 0 && (
              <Button onClick={handleViewResults}>
                View Results ({completedCount} document{completedCount > 1 ? 's' : ''})
              </Button>
            )}
          </div>
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
