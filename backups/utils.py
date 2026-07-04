import gzip
import os
import subprocess
import datetime
from django.conf import settings


def run_backup(school_slug):
    """
    Runs pg_dump for SQLite (dev) or PostgreSQL (prod).
    Returns (filepath, filename, file_size_bytes, error_message)
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{school_slug}_{timestamp}.sql.gz"
    backup_dir = os.path.join(settings.MEDIA_ROOT, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    filepath = os.path.join(backup_dir, filename)

    db = settings.DATABASES["default"]
    engine = db["ENGINE"]

    try:
        if "sqlite3" in engine:
            # SQLite — just copy the db file compressed
            db_path = str(db["NAME"])
            with open(db_path, "rb") as f_in:
                with gzip.open(filepath, "wb") as f_out:
                    f_out.write(f_in.read())

        elif "postgresql" in engine:
            env = os.environ.copy()
            env["PGPASSWORD"] = db.get("PASSWORD", "")
            cmd = [
                "pg_dump",
                "-h",
                db.get("HOST", "localhost"),
                "-p",
                str(db.get("PORT", "5432")),
                "-U",
                db.get("USER", "postgres"),
                db.get("NAME", ""),
            ]
            with gzip.open(filepath, "wb") as f_out:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                )
                if result.returncode != 0:
                    return None, filename, None, result.stderr.decode()
                f_out.write(result.stdout)
        else:
            return None, filename, None, f"Unsupported database engine: {engine}"

        file_size = os.path.getsize(filepath)
        return filepath, filename, file_size, ""

    except Exception as e:
        return None, filename, None, str(e)
