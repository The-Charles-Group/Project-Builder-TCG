import os
from pathlib import Path


def get_database_url():
    """
    Get the database URL for the current environment.
    
    In production (when published), Replit stores the database URL in /tmp/replitdb.
    In development, it uses the DATABASE_URL environment variable.
    
    This function automatically detects which environment we're in and returns
    the appropriate database URL.
    
    Returns:
        str: The database connection URL
    """
    production_db_file = Path("/tmp/replitdb")
    
    if production_db_file.exists():
        with open(production_db_file, 'r') as f:
            db_url = f.read().strip()
            print("Using PRODUCTION database from /tmp/replitdb")
            return db_url
    
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        print("Using DEVELOPMENT database from DATABASE_URL")
        return db_url
    
    raise ValueError(
        "No database URL found. "
        "Ensure DATABASE_URL is set in development or /tmp/replitdb exists in production."
    )


def get_connection_params():
    """
    Get individual database connection parameters.
    
    Returns:
        dict: Dictionary with host, port, user, password, database
    """
    production_db_file = Path("/tmp/replitdb")
    
    if production_db_file.exists():
        print("Using PRODUCTION database parameters")
        db_url = get_database_url()
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip('/'),
        }
    else:
        print("Using DEVELOPMENT database parameters")
        return {
            "host": os.environ.get("PGHOST"),
            "port": int(os.environ.get("PGPORT", 5432)),
            "user": os.environ.get("PGUSER"),
            "password": os.environ.get("PGPASSWORD"),
            "database": os.environ.get("PGDATABASE"),
        }
