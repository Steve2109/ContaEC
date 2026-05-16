"""Backups automáticos cifrados para ContaEC."""
import asyncio
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.core.security import get_fernet


class BackupService:
    """Genera un respaldo diario exportable y cifrado."""

    @staticmethod
    def cleanup_temp_files() -> None:
        ttl = timedelta(minutes=settings.TEMP_FILE_TTL_MINUTES)
        folders = [settings.TEMP_UPLOAD_FOLDER, settings.EXPORT_TEMP_FOLDER]
        now = datetime.now(timezone.utc)
        for folder in folders:
            base = Path(folder)
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if now - modified > ttl:
                    path.unlink(missing_ok=True)

    @staticmethod
    def create_encrypted_backup() -> Path:
        backup_dir = Path(settings.BACKUP_FOLDER)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dump_path = backup_dir / f"contaec_{timestamp}.sql"
        encrypted_path = backup_dir / f"contaec_{timestamp}.sql.enc"

        if shutil.which("pg_dump"):
            parsed = urlparse(settings.DATABASE_URL)
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password or ""
            command = [
                "pg_dump",
                "-h", parsed.hostname or "localhost",
                "-p", str(parsed.port or 5432),
                "-U", parsed.username or "postgres",
                "-d", (parsed.path or "/").lstrip("/"),
                "-f", str(dump_path),
            ]
            subprocess.run(command, check=True, env=env, timeout=1800)
            raw = dump_path.read_bytes()
            dump_path.unlink(missing_ok=True)
        else:
            raw = b"pg_dump no disponible; instale postgresql-client para backups completos."

        encrypted_path.write_bytes(get_fernet().encrypt(raw))
        return encrypted_path

    @staticmethod
    async def run_midnight_scheduler() -> None:
        while True:
            BackupService.cleanup_temp_files()
            now = datetime.now()
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            await asyncio.sleep(max((next_midnight - now).total_seconds(), 60))
            try:
                BackupService.create_encrypted_backup()
            finally:
                BackupService.cleanup_temp_files()
