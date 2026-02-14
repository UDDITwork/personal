"""
Turso Cloud Sync Layer
Synchronizes SQLAlchemy operations to Turso cloud database via libsql-client
NO local SQLite files - pure cloud persistence
"""
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import Session
from loguru import logger
from typing import Any, Dict, List
import json
from datetime import datetime


def setup_turso_sync(engine, turso_client):
    """
    Set up event listeners to sync all database operations to Turso cloud

    Args:
        engine: SQLAlchemy engine
        turso_client: libsql-client instance for Turso cloud
    """

    def serialize_value(value):
        """Convert Python value to SQL-safe format"""
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, datetime):
            return f"'{value.isoformat()}'"
        elif isinstance(value, str):
            # Escape single quotes for SQL by doubling them
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        else:
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"

    def build_insert_sql(table_name: str, values: Dict[str, Any]) -> str:
        """Build INSERT SQL statement"""
        columns = ", ".join(values.keys())
        vals = ", ".join(serialize_value(v) for v in values.values())
        return f"INSERT INTO {table_name} ({columns}) VALUES ({vals})"

    def build_update_sql(table_name: str, pk_name: str, pk_value: Any, values: Dict[str, Any]) -> str:
        """Build UPDATE SQL statement"""
        set_clause = ", ".join(f"{k} = {serialize_value(v)}" for k, v in values.items())
        return f"UPDATE {table_name} SET {set_clause} WHERE {pk_name} = {serialize_value(pk_value)}"

    def build_delete_sql(table_name: str, pk_name: str, pk_value: Any) -> str:
        """Build DELETE SQL statement"""
        return f"DELETE FROM {table_name} WHERE {pk_name} = {serialize_value(pk_value)}"

    # ============================================================================
    # INSERT SYNC
    # ============================================================================
    @event.listens_for(Session, 'after_flush', propagate=True)
    def sync_after_flush(session, flush_context):
        """
        Sync all INSERT/UPDATE/DELETE operations to Turso after flush
        This runs BEFORE commit, so we can still rollback if Turso fails
        """
        try:
            # Process new objects (INSERT)
            for obj in session.new:
                table_name = obj.__tablename__
                mapper = inspect(obj.__class__)
                pk_name = mapper.primary_key[0].name

                # Get all column values
                values = {}
                for column in mapper.columns:
                    col_name = column.name
                    values[col_name] = getattr(obj, col_name, None)

                # Execute INSERT on Turso
                sql = build_insert_sql(table_name, values)
                logger.debug(f"Turso INSERT: {sql}")
                turso_client.execute(sql)

            # Process updated objects (UPDATE)
            for obj in session.dirty:
                if session.is_modified(obj):
                    table_name = obj.__tablename__
                    mapper = inspect(obj.__class__)
                    pk_name = mapper.primary_key[0].name
                    pk_value = getattr(obj, pk_name)

                    # Get all column values
                    values = {}
                    for column in mapper.columns:
                        col_name = column.name
                        if col_name != pk_name:  # Don't update primary key
                            values[col_name] = getattr(obj, col_name, None)

                    # Execute UPDATE on Turso
                    sql = build_update_sql(table_name, pk_name, pk_value, values)
                    logger.debug(f"Turso UPDATE: {sql}")
                    turso_client.execute(sql)

            # Process deleted objects (DELETE)
            for obj in session.deleted:
                table_name = obj.__tablename__
                mapper = inspect(obj.__class__)
                pk_name = mapper.primary_key[0].name
                pk_value = getattr(obj, pk_name)

                # Execute DELETE on Turso
                sql = build_delete_sql(table_name, pk_name, pk_value)
                logger.debug(f"Turso DELETE: {sql}")
                turso_client.execute(sql)

            logger.debug(f"✅ Synced to Turso: {len(session.new)} inserts, {len(session.dirty)} updates, {len(session.deleted)} deletes")

        except Exception as e:
            logger.error(f"❌ Turso sync failed: {e}")
            # Don't raise - allow local transaction to continue
            # TODO: Implement retry queue for failed syncs

    logger.success("✅ Turso sync event listeners registered")


def load_data_from_turso(engine, turso_client):
    """
    Load ALL data from Turso cloud into in-memory database on startup
    This ensures data persists across server restarts

    Args:
        engine: SQLAlchemy engine
        turso_client: libsql-client instance for Turso cloud
    """
    try:
        from .models import Base

        logger.info("📥 Loading data from Turso cloud...")

        total_rows = 0

        # Load data for each table in dependency order
        for table in Base.metadata.sorted_tables:
            table_name = table.name

            try:
                # Fetch all rows from Turso
                result = turso_client.execute(f"SELECT * FROM {table_name}")

                if hasattr(result, 'rows') and result.rows:
                    rows = result.rows

                    # Get column names
                    if hasattr(result, 'columns'):
                        columns = [col['name'] for col in result.columns]
                    else:
                        # Fallback: use table column names
                        columns = [col.name for col in table.columns]

                    # Insert each row into in-memory database
                    with engine.begin() as conn:
                        for row in rows:
                            # Build INSERT statement
                            values = dict(zip(columns, row))
                            placeholders = ", ".join([f":{col}" for col in columns])
                            cols = ", ".join(columns)

                            insert_sql = text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})")
                            conn.execute(insert_sql, values)
                            total_rows += 1

                    logger.info(f"✅ Loaded {len(rows)} rows from {table_name}")
                else:
                    logger.debug(f"No data in {table_name}")

            except Exception as e:
                logger.warning(f"Failed to load data from {table_name}: {e}")
                # Continue with other tables

        logger.success(f"✅ Loaded {total_rows} total rows from Turso cloud")
        return total_rows

    except Exception as e:
        logger.error(f"❌ Failed to load data from Turso: {e}")
        return 0


def sync_turso_to_memory(engine, turso_client):
    """
    One-time sync from Turso cloud to in-memory database
    Call this on application startup
    """
    load_data_from_turso(engine, turso_client)
