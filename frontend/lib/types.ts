export interface User {
  id: string;
  email: string;
  full_name?: string;
  created_at: string;
  is_active: boolean;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  session_id: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
}

export interface Document {
  id: string;
  project_id: string;
  document_type: 'idf' | 'transcription' | 'claims';
  file_name: string;
  file_type: 'pdf' | 'docx';
  file_path: string;
  file_size_bytes: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at: string;
  extraction?: Extraction;
}

export interface Extraction {
  id: string;
  document_id: string;
  extracted_text_markdown?: string;
  extracted_text_plain?: string;
  total_pages: number;
  confidence_score?: number;
  llamaparse_time?: number;
  pymupdf_time?: number;
  gemini_time?: number;
  total_time?: number;
  extraction_method?: string;
  extraction_metadata?: any;
  images: ExtractedImage[];
  tables: ExtractedTable[];
  diagrams: DiagramDescription[];
}

export interface ExtractedImage {
  id?: string;
  extraction_id?: string;
  image_id: string;
  page_number: number;
  image_path: string;
  presigned_url?: string;
  image_type?: string;
  width?: number;
  height?: number;
  diagram_description?: string;
}

export interface ExtractedTable {
  id?: string;
  extraction_id?: string;
  table_id: string;
  page_number: number;
  html_content: string;
  headers_json?: string;
  rows_json?: string;
  num_rows: number;
  num_cols: number;
  b_box_x?: number;
  b_box_y?: number;
  b_box_width?: number;
  b_box_height?: number;
  extraction_source?: string;
}

export interface DiagramDescription {
  id?: string;
  extraction_id?: string;
  image_id: string;
  is_diagram: boolean;
  diagram_type?: string;
  outermost_elements: string[] | string;
  shape_mapping?: any;
  nested_components?: any;
  connections: any[] | string;
  all_text_labels: string[] | string;
  description_summary: string;
  image_type?: string;
}

// API Response types matching backend AuthResponse
export interface LoginResponse {
  success: boolean;
  message: string;
  access_token: string;
  token_type: string;
  expires_at: string;
  user: {
    id: string;
    email: string;
    full_name: string;
  };
}

export interface RegisterResponse {
  success: boolean;
  message: string;
  access_token?: string;
  token_type?: string;
  expires_at?: string;
  user: {
    id: string;
    email: string;
    full_name: string;
  };
}

export interface ProjectsResponse {
  projects: Project[];
}

export interface UploadResponse {
  success: boolean;
  message: string;
  document_id: string;
  project_id: string;
  document_type: string;
  file_name: string;
  file_path: string;
  processing_status: string;
}

// Error response type for API errors
export interface ErrorResponse {
  detail: string;
}

// Logout response
export interface LogoutResponse {
  success: boolean;
  message: string;
}
