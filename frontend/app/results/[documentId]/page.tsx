'use client';

import { use, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, FileText, Image as ImageIcon, Table as TableIcon, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface Document {
  id: string;
  file_name: string;
  file_type: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  extraction?: {
    extracted_text_markdown?: string;
    extracted_text_plain?: string;
    total_pages: number;
    confidence_score?: number;
    total_time?: number;
    images: Array<{
      image_id: string;
      page_number: number;
      presigned_url: string;
      diagram_description?: string;
      width?: number;
      height?: number;
    }>;
    tables: Array<{
      table_id: string;
      page_number: number;
      html_content: string;
      num_rows: number;
      num_cols: number;
    }>;
    diagrams: Array<{
      image_id: string;
      diagram_type?: string;
      description_summary: string;
      outermost_elements?: string[];
    }>;
  };
}

export default function ResultsPage({ params }: { params: Promise<{ documentId: string }> }) {
  const resolvedParams = use(params);
  const documentId = resolvedParams.documentId;
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();

  const projectId = searchParams.get('project');
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
      return;
    }

    if (!projectId) {
      setError('Project ID is missing');
      setLoading(false);
      return;
    }

    fetchDocument();
    const interval = setInterval(() => {
      if (document?.processing_status === 'pending' || document?.processing_status === 'processing') {
        fetchDocument();
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [documentId, projectId, isAuthenticated, document?.processing_status]);

  const fetchDocument = async () => {
    if (!projectId) return;

    try {
      const response = await api.get<Document>(`/projects/${projectId}/documents/${documentId}`);
      setDocument(response.data);
      setLoading(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load document');
      setLoading(false);
    }
  };

  if (loading && !document) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center text-red-600">
              <AlertCircle className="w-5 h-5 mr-2" />
              Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Document not found</p>
      </div>
    );
  }

  const getStatusBadge = () => {
    switch (document.processing_status) {
      case 'completed':
        return <Badge className="bg-green-500">Completed</Badge>;
      case 'processing':
        return <Badge className="bg-blue-500">Processing</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500">Pending</Badge>;
      case 'failed':
        return <Badge className="bg-red-500">Failed</Badge>;
      default:
        return <Badge>{document.processing_status}</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Extraction Results</h1>
          <p className="text-slate-600 mt-1">
            {document.file_name}
          </p>
        </div>

        {/* Status Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Processing Status</CardTitle>
              {getStatusBadge()}
            </div>
          </CardHeader>
          <CardContent>
            {(document.processing_status === 'pending' || document.processing_status === 'processing') && (
              <div className="space-y-2">
                <Progress value={document.processing_status === 'pending' ? 25 : 50} />
                <p className="text-sm text-slate-600 flex items-center">
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  {document.processing_status === 'pending' ? 'Waiting to process...' : 'Extracting data...'}
                </p>
              </div>
            )}

            {document.processing_status === 'failed' && (
              <div className="text-red-600">
                <p>Extraction failed: {document.error_message || 'Unknown error'}</p>
              </div>
            )}

            {document.processing_status === 'completed' && document.extraction && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-slate-600">Pages</p>
                  <p className="text-2xl font-bold">{document.extraction.total_pages}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-600">Images</p>
                  <p className="text-2xl font-bold">{document.extraction.images.length}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-600">Tables</p>
                  <p className="text-2xl font-bold">{document.extraction.tables.length}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-600">Processing Time</p>
                  <p className="text-2xl font-bold">
                    {document.extraction.total_time ? `${(document.extraction.total_time / 1000).toFixed(1)}s` : 'N/A'}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Tabs */}
        {document.processing_status === 'completed' && document.extraction && (
          <Tabs defaultValue="text" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="text">
                <FileText className="w-4 h-4 mr-2" />
                Text
              </TabsTrigger>
              <TabsTrigger value="images">
                <ImageIcon className="w-4 h-4 mr-2" />
                Images ({document.extraction.images.length})
              </TabsTrigger>
              <TabsTrigger value="tables">
                <TableIcon className="w-4 h-4 mr-2" />
                Tables ({document.extraction.tables.length})
              </TabsTrigger>
            </TabsList>

            {/* Text Content */}
            <TabsContent value="text" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Extracted Text</CardTitle>
                  <CardDescription>Full document text extraction</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="prose max-w-none">
                    {document.extraction.extracted_text_markdown ? (
                      <div className="whitespace-pre-wrap">
                        {document.extraction.extracted_text_markdown}
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">
                        {document.extraction.extracted_text_plain}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Images Content */}
            <TabsContent value="images" className="mt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {document.extraction.images.map((image) => (
                  <Card key={image.image_id}>
                    <CardHeader>
                      <CardTitle className="text-sm">Page {image.page_number}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <img
                        src={image.presigned_url}
                        alt={`Page ${image.page_number} - ${image.image_id}`}
                        className="w-full h-auto rounded"
                      />
                      {image.diagram_description && (
                        <p className="text-sm text-slate-600 mt-2">
                          {image.diagram_description}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* Tables Content */}
            <TabsContent value="tables" className="mt-6">
              <div className="space-y-6">
                {document.extraction.tables.map((table) => (
                  <Card key={table.table_id}>
                    <CardHeader>
                      <CardTitle className="text-sm">
                        Page {table.page_number} - {table.num_rows} rows × {table.num_cols} cols
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div
                        className="overflow-x-auto"
                        dangerouslySetInnerHTML={{ __html: table.html_content }}
                      />
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}
