# Migrating to Turso Cloud Database

## Current Status

Your PATMASTER application is currently using a **local SQLite database** (`patmaster_auth.db`) for testing and development. All functionality is working correctly with local storage.

## Turso Configuration

Your Turso database credentials are already configured in the `.env` file:

```env
TURSO_DATABASE_URL=https://monitoring-of-ibm-uddit.aws-ap-south-1.turso.io
TURSO_AUTH_TOKEN=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...
```

## Migration Steps

### Option 1: Using Turso with HTTP Endpoint (Recommended for Production)

Turso provides an HTTP API that can be used without SQLAlchemy. This is the most reliable approach.

#### Step 1: Install Turso Platform SDK
```bash
pip install turso-platform-sdk
```

#### Step 2: Create Turso Database Adapter

Create `database/turso_adapter.py`:
```python
from turso_platform import TursoPlatform
import os

# Initialize Turso client
client = TursoPlatform(
    database_url=os.getenv("TURSO_DATABASE_URL"),
    auth_token=os.getenv("TURSO_AUTH_TOKEN")
)

# Use this for direct SQL queries to Turso
# This bypasses SQLAlchemy for production deployments
```

### Option 2: Using sqlalchemy-libsql (For Full ORM Support)

This approach maintains full SQLAlchemy ORM compatibility but requires additional setup.

#### Step 1: Install sqlalchemy-libsql
```bash
pip install sqlalchemy-libsql
```

**Note**: This installation can take 5-10 minutes as it builds the libsql-experimental package.

#### Step 2: Update `database/connection.py`

Replace the engine configuration with:

```python
# Turso database URL with libsql protocol
TURSO_DATABASE_URL = os.getenv(
    "TURSO_DATABASE_URL",
    "https://monitoring-of-ibm-uddit.aws-ap-south-1.turso.io"
)

TURSO_AUTH_TOKEN = os.getenv(
    "TURSO_AUTH_TOKEN",
    ""
)

# Remove https:// prefix for libsql protocol
database_name = TURSO_DATABASE_URL.replace("https://", "")

# Construct libsql connection string
DATABASE_URL = f"sqlite+libsql://{database_name}?authToken={TURSO_AUTH_TOKEN}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    },
    pool_pre_ping=True,
    echo=False
)
```

#### Step 3: Run Database Migrations on Turso

```bash
# Apply all migrations to Turso database
alembic upgrade head
```

### Option 3: Hybrid Approach (Current Setup + Turso Sync)

Keep local SQLite for development and sync to Turso for production.

1. Develop locally with `patmaster_auth.db`
2. Use Alembic migrations to keep schema in sync
3. Periodically export local data and import to Turso
4. Switch to Turso URL in production `.env`

## Testing Turso Connection

Create `test_turso_connection.py`:

```python
"""Test Turso database connection"""
import os
from sqlalchemy import create_engine, text

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Remove https:// and construct libsql URL
database_name = TURSO_DATABASE_URL.replace("https://", "")
connection_url = f"sqlite+libsql://{database_name}?authToken={TURSO_AUTH_TOKEN}"

print(f"Connecting to: {database_name}")

try:
    engine = create_engine(connection_url)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Turso connection successful!")

except Exception as e:
    print(f"❌ Turso connection failed: {e}")
```

Run with:
```bash
python test_turso_connection.py
```

## Production Deployment Checklist

- [ ] Install `sqlalchemy-libsql` package
- [ ] Update `database/connection.py` with Turso URL
- [ ] Run `alembic upgrade head` to create tables on Turso
- [ ] Test connection with `test_turso_connection.py`
- [ ] Update `.env` with production Turso credentials
- [ ] Verify all CRUD operations work with Turso
- [ ] Monitor connection pool and query performance
- [ ] Set up Turso backups and point-in-time recovery

## Turso Features

Your Turso database includes:

- **Global Distribution**: Edge replicas for low latency
- **Branching**: Create database branches for testing
- **Point-in-Time Recovery**: Restore to any point in last 24 hours
- **SQL Console**: Web-based SQL interface at https://turso.tech
- **Vector Search**: Built-in vector embeddings (if needed for future features)

## Current Database Schema

The following tables will be created on Turso:

1. **users** - User accounts with authentication
2. **user_sessions** - JWT token sessions
3. **projects** - Patent application projects
4. **documents** - Uploaded documents (IDF, Transcription, Claims)
5. **extractions** - Extraction results from pipeline
6. **extracted_images** - Images from documents
7. **diagram_descriptions** - Structured diagram analysis
8. **extracted_tables** - Tables from documents

All tables are created automatically via Alembic migrations.

## Performance Considerations

### Local SQLite (Current)
- ✅ Fast for development (no network latency)
- ✅ Simple setup
- ❌ Single machine only
- ❌ No redundancy

### Turso Cloud
- ✅ Distributed and replicated
- ✅ Accessible from anywhere
- ✅ Automatic backups
- ✅ Scalable
- ⚠️  Network latency (mitigated by edge locations)

## Troubleshooting

### "Module 'bcrypt' has no attribute '__about__'"
This is a warning and can be ignored. The application still works correctly.

### "Could not establish connection to Turso"
1. Verify TURSO_AUTH_TOKEN is correct
2. Check network connectivity
3. Ensure database URL matches Turso dashboard
4. Try regenerating the auth token in Turso dashboard

### "Table already exists"
Run: `alembic downgrade base && alembic upgrade head`

## Support

For Turso-specific issues:
- Turso Documentation: https://docs.turso.tech
- Turso Discord: https://discord.gg/turso
- GitHub Issues: https://github.com/tursodatabase/libsql

For application issues:
- Check logs in `logs/extraction_*.log`
- Review Alembic migration status: `alembic current`
- Test with local SQLite first to isolate Turso-specific issues

## Next Steps

1. **Immediate**: Continue using local SQLite for development
2. **Before Production**: Migrate to Turso using Option 2 above
3. **Production**: Monitor Turso dashboard for query performance and connection stats

Your authentication system is **production-ready** and can be deployed with either local SQLite or Turso cloud database!
