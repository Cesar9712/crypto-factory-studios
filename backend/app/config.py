from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os

def _origins() -> tuple[str, ...]:
    raw=os.getenv('CFS_ALLOWED_ORIGINS','').strip()
    if raw: return tuple(x.strip().rstrip('/') for x in raw.split(',') if x.strip())
    return ('http://localhost:8000','http://127.0.0.1:8000','https://crypto-factory-studios.cesargp9712.workers.dev')

@dataclass
class Settings:
    root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    database_path: Path = field(init=False)
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL','').strip())
    storage_backend: str = field(default_factory=lambda: os.getenv('CFS_STORAGE_BACKEND','local').lower().strip())
    s3_endpoint_url: str = field(default_factory=lambda: os.getenv('CFS_S3_ENDPOINT_URL','').strip())
    s3_region: str = field(default_factory=lambda: os.getenv('CFS_S3_REGION','auto').strip() or 'auto')
    s3_bucket: str = field(default_factory=lambda: os.getenv('CFS_S3_BUCKET','').strip())
    s3_access_key_id: str = field(default_factory=lambda: os.getenv('CFS_S3_ACCESS_KEY_ID','').strip())
    s3_secret_access_key: str = field(default_factory=lambda: os.getenv('CFS_S3_SECRET_ACCESS_KEY','').strip())
    quarantine_dir: Path = field(init=False)
    published_dir: Path = field(init=False)
    session_seconds: int = 86400
    max_upload_bytes: int = 64*1024*1024
    max_uncompressed_bytes: int = 256*1024*1024
    max_archive_files: int = 3000
    max_compression_ratio: float = 80.0
    allowed_origins: tuple[str,...] = field(default_factory=_origins)
    environment: str = field(default_factory=lambda: os.getenv('CFS_ENV','development').lower().strip())
    owner_bootstrap_token: str = field(default_factory=lambda: os.getenv('CFS_OWNER_BOOTSTRAP_TOKEN',''))
    # External ClamAV-style scanning is intentionally opt-in. The former
    # CFS_ANTIVIRUS_REQUIRED flag is no longer consumed because it caused the
    # 512 MB Render Free instance to fail uploads by exhausting memory. The
    # built-in streaming/static scanner remains active for every upload.
    antivirus_required: bool = field(default_factory=lambda: os.getenv('CFS_EXTERNAL_ANTIVIRUS_REQUIRED','false').lower()=='true')
    payments_mode: str = field(default_factory=lambda: os.getenv('CFS_PAYMENTS_MODE','MOCK'))
    production_payments_enabled: bool = field(default_factory=lambda: os.getenv('CFS_PRODUCTION_PAYMENTS_ENABLED','false').lower()=='true')
    tron_usdt_address: str = field(default_factory=lambda: os.getenv('CFS_TRON_USDT_ADDRESS','TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9'))
    bsc_usdt_address: str = field(default_factory=lambda: os.getenv('CFS_BSC_USDT_ADDRESS','0xb6e727732F845bDb7792C075B147658e84a173d2'))
    sol_address: str = field(default_factory=lambda: os.getenv('CFS_SOL_ADDRESS','EpiJ5GUjXMhcQpZtErxwGq5VZKwvkxV8kSz8PUKtpsr2'))
    mock_sol_usd_rate: str = field(default_factory=lambda: os.getenv('CFS_MOCK_SOL_USD_RATE','150.00'))
    quote_seconds: int = 900
    order_seconds: int = 1800

    def __post_init__(self):
        self.database_path=Path(os.getenv('CFS_DATABASE_PATH',str(self.root/'database'/'cfs.db')))
        self.quarantine_dir=Path(os.getenv('CFS_QUARANTINE_DIR',str(self.root/'storage'/'quarantine')))
        self.published_dir=Path(os.getenv('CFS_PUBLISHED_DIR',str(self.root/'storage'/'published')))
        self.database_path.parent.mkdir(parents=True,exist_ok=True); self.quarantine_dir.mkdir(parents=True,exist_ok=True); self.published_dir.mkdir(parents=True,exist_ok=True)
        self.payments_mode=self.payments_mode.upper().strip()
        if self.environment not in {'development','test','production'}: raise RuntimeError('Invalid CFS_ENV')
        if self.storage_backend not in {'local','s3'}: raise RuntimeError('Invalid CFS_STORAGE_BACKEND')
        if self.payments_mode not in {'MOCK','TEST','PRODUCTION'}: raise RuntimeError('Invalid CFS_PAYMENTS_MODE')
        if self.environment=='production' and not self.owner_bootstrap_token: raise RuntimeError('Production requires CFS_OWNER_BOOTSTRAP_TOKEN')
        if self.environment=='production' and not self.database_url: raise RuntimeError('Production requires DATABASE_URL for persistent database storage')
        if self.environment=='production' and self.storage_backend=='local': raise RuntimeError('Production requires persistent object storage; set CFS_STORAGE_BACKEND=s3')
        if self.storage_backend=='s3':
            missing=[name for name,val in [('CFS_S3_ENDPOINT_URL',self.s3_endpoint_url),('CFS_S3_BUCKET',self.s3_bucket),('CFS_S3_ACCESS_KEY_ID',self.s3_access_key_id),('CFS_S3_SECRET_ACCESS_KEY',self.s3_secret_access_key)] if not val]
            if missing: raise RuntimeError('Missing S3 storage settings: '+','.join(missing))
        if self.payments_mode=='PRODUCTION' and not self.production_payments_enabled: raise RuntimeError('Production payments require CFS_PRODUCTION_PAYMENTS_ENABLED=true')
        if self.payments_mode=='PRODUCTION': raise RuntimeError('Production crypto verifier is intentionally disabled until on-chain verification is implemented')
