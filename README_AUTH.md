# PATMASTER Multi-Tenant Authentication System

## Overview

The PATMASTER Document Extraction API now includes a complete multi-tenant authentication system with JWT-based authentication, project management, and document upload capabilities.

## Architecture

### Database Schema

The system uses 8 SQLAlchemy models stored in Turso SQLite:

1. **User** - User accounts with email/password authentication
2. **UserSession** - JWT token sessions for authentication
3. **Project** - User projects containing documents
4. **Document** - Documents uploaded to projects (IDF, Transcription, Claims)
5. **Extraction** - Extraction results from document processing
6. **ExtractedImage** - Images extracted from documents
7. **DiagramDescription** - Structured diagram descriptions
8. **ExtractedTable** - Tables extracted from documents

### Security Features

- **JWT Authentication**: Secure token-based authentication with 30-minute expiry
- **Password Hashing**: bcrypt with custom salt for each user
- **Row-Level Security**: Users can only access their own projects and documents
- **Multi-Tenant Isolation**: Complete data isolation between users

## API Endpoints

### Authentication

#### Register New User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

Response:
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": "2026-02-14T12:30:00",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

#### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <your_token>
```

#### Get Current User Info
```http
GET /api/v1/auth/me
Authorization: Bearer <your_token>
```

### Project Management

#### Create Project
```http
POST /api/v1/projects
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "name": "Patent Application 2024-001",
  "description": "AI-based medical diagnosis system"
}
```

#### List All Projects
```http
GET /api/v1/projects
Authorization: Bearer <your_token>
```

#### Get Project Details
```http
GET /api/v1/projects/{project_id}
Authorization: Bearer <your_token>
```

#### Update Project
```http
PUT /api/v1/projects/{project_id}
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "name": "Updated Project Name",
  "description": "Updated description"
}
```

#### Delete Project
```http
DELETE /api/v1/projects/{project_id}
Authorization: Bearer <your_token>
```

### Document Upload

#### Upload IDF Document (PDF)
```http
POST /api/v1/projects/{project_id}/upload/idf
Authorization: Bearer <your_token>
Content-Type: multipart/form-data

file: <your_idf.pdf>
```

#### Upload Transcription Document (DOCX)
```http
POST /api/v1/projects/{project_id}/upload/transcription
Authorization: Bearer <your_token>
Content-Type: multipart/form-data

file: <your_transcription.docx>
```

#### Upload Claims Document (DOCX)
```http
POST /api/v1/projects/{project_id}/upload/claims
Authorization: Bearer <your_token>
Content-Type: multipart/form-data

file: <your_claims.docx>
```

#### Get Document Details
```http
GET /api/v1/projects/{project_id}/documents/{document_id}
Authorization: Bearer <your_token>
```

#### Delete Document
```http
DELETE /api/v1/projects/{project_id}/documents/{document_id}
Authorization: Bearer <your_token>
```

## Usage Flow

### 1. Register and Login

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
  }'

# Login to get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'

# Save the access_token from response
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. Create a Project

```bash
# Create a new project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Patent Application 2024-001",
    "description": "AI-based medical diagnosis system"
  }'

# Save the project id from response
PROJECT_ID="uuid"
```

### 3. Upload Documents

```bash
# Upload IDF document (PDF)
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/upload/idf \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/idf_document.pdf"

# Upload Transcription document (DOCX)
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/upload/transcription \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/transcription.docx"

# Upload Claims document (DOCX)
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT_ID/upload/claims \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/claims.docx"
```

### 4. View Results

```bash
# Get project details with all documents
curl -X GET http://localhost:8000/api/v1/projects/$PROJECT_ID \
  -H "Authorization: Bearer $TOKEN"

# Get specific document with extraction results
curl -X GET http://localhost:8000/api/v1/projects/$PROJECT_ID/documents/$DOCUMENT_ID \
  -H "Authorization: Bearer $TOKEN"
```

## File Naming Convention

All uploaded files are saved with the following naming pattern:
```
{user_id}_{session_id}_{document_type}.{extension}
```

Examples:
- `82fc2e05-72c4-4736-92b1-6176a4b4ea0b_a1b2c3d4-e5f6-7890-abcd-ef1234567890_idf.pdf`
- `82fc2e05-72c4-4736-92b1-6176a4b4ea0b_a1b2c3d4-e5f6-7890-abcd-ef1234567890_transcription.docx`
- `82fc2e05-72c4-4736-92b1-6176a4b4ea0b_a1b2c3d4-e5f6-7890-abcd-ef1234567890_claims.docx`

## Document Processing Pipeline

When a document is uploaded:

1. **File Validation**: Checks file type (PDF for IDF, DOCX for Transcription/Claims)
2. **Storage**: Saves file to disk with unique naming convention
3. **Database Record**: Creates Document record in database
4. **Extraction Pipeline**: (To be triggered)
   - PDF: Uses hybrid triple-layer extraction (LlamaParse V1 + LlamaCloud V2 + PyMuPDF)
   - DOCX: Uses DOCX extractor with text and table extraction
   - Gemini Vision: Describes diagrams and images
5. **Results Storage**: Saves extraction results to Extraction, ExtractedImage, DiagramDescription, and ExtractedTable tables
6. **Status Update**: Updates document status to "completed" or "failed"

## Database Configuration

### Local Development (SQLite)
By default, the application uses a local SQLite database at:
```
./patmaster_auth.db
```

### Production (Turso)
For production deployment, update the `.env` file:
```env
TURSO_DATABASE_URL=https://your-database.turso.io
TURSO_AUTH_TOKEN=your_turso_auth_token
```

Then update `database/connection.py` to use Turso instead of local SQLite.

## Environment Variables

Required environment variables in `.env`:

```env
# API Keys
LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
GEMINI_API_KEY=your_gemini_api_key

# Database
TURSO_DATABASE_URL=https://your-database.turso.io
TURSO_AUTH_TOKEN=your_turso_auth_token

# JWT Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_min_32_chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_URL=redis://localhost:6379/0

# Processing
MAX_CONCURRENT_EXTRACTIONS=50
EXTRACTION_TIMEOUT=300
DIAGRAM_DESCRIPTION_TIMEOUT=60

# Environment
ENVIRONMENT=development
```

## Database Migrations

### Create a New Migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

## Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security Best Practices

1. **JWT Secret Key**: Use a strong, random secret key (minimum 32 characters)
2. **HTTPS**: Always use HTTPS in production
3. **CORS**: Configure specific allowed origins instead of wildcard (*)
4. **Password Policy**: Enforce minimum 8-character passwords
5. **Token Expiry**: Tokens expire after 30 minutes (configurable)
6. **Database Isolation**: Row-level security ensures users can only access their own data

## Troubleshooting

### "Could not validate credentials"
- Check if token has expired (30-minute default)
- Verify token is included in Authorization header as: `Bearer <token>`

### "Project not found"
- Ensure you're using the correct project_id
- Verify you have permission to access the project (row-level security)

### "Email already registered"
- Use a different email address
- Or login with existing credentials

### Database Connection Issues
- Check if `.env` file exists with correct database configuration
- Verify Turso credentials are valid
- Check network connectivity to Turso database

## Next Steps

1. **Deploy to Production**: Update database connection to use Turso
2. **Enable Background Processing**: Integrate Celery for async extraction
3. **Add Email Verification**: Implement email verification for new users
4. **Implement Rate Limiting**: Add rate limiting to prevent abuse
5. **Add Document Versioning**: Allow multiple versions of the same document type
6. **Implement Webhooks**: Notify users when extraction completes

## Support

For issues or questions, please refer to:
- API Documentation: http://localhost:8000/docs
- Main README: README.md
- GitHub Issues: https://github.com/your-repo/issues
