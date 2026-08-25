from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os

def _origins() -> tuple[str, ...]:
    raw=os.getenv('CFS_ALLOWED_ORIGINS','').strip()
    if raw: return tuple(x.strip().rstrip('/') for x in raw.split(',') if x.strip())
    return ('http://localhost:8000','http://127.0.0.1:8000','https://crypto-factory-studios.cesargp9712.workers.dev')

def _csv_env(name: str) -> tuple[str, ...]:
    raw=os.getenv(name,'').strip()
    return tuple(x.strip() for x in raw.split(',') if x.strip()) if raw else ()

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
    antivirus_required: bool = field(default_factory=lambda: os.getenv('CFS_EXTERNAL_ANTIVIRUS_REQUIRED','false').lower()=='true')
    payments_mode: str = field(default_factory=lambda: os.getenv('CFS_PAYMENTS_MODE','MOCK'))
    production_payments_enabled: bool = field(default_factory=lambda: os.getenv('CFS_PRODUCTION_PAYMENTS_ENABLED','false').lower()=='true')
    deposit_address_mode: str = field(default_factory=lambda: os.getenv('CFS_DEPOSIT_ADDRESS_MODE','SHARED_MARKER').upper().strip())
    tron_usdt_address: str = field(default_factory=lambda: os.getenv('CFS_TRON_USDT_ADDRESS','TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9'))
    bsc_usdt_address: str = field(default_factory=lambda: os.getenv('CFS_BSC_USDT_ADDRESS','0xb6e727732F845bDb7792C075B147658e84a173d2'))
    sol_address: str = field(default_factory=lambda: os.getenv('CFS_SOL_ADDRESS','EpiJ5GUjXMhcQpZtErxwGq5VZKwvkxV8kSz8PUKtpsr2'))
    tron_deposit_addresses: tuple[str,...] = field(default_factory=lambda: _csv_env('CFS_TRON_DEPOSIT_ADDRESSES'))
    bsc_deposit_addresses: tuple[str,...] = field(default_factory=lambda: _csv_env('CFS_BSC_DEPOSIT_ADDRESSES'))
    sol_deposit_addresses: tuple[str,...] = field(default_factory=lambda: _csv_env('CFS_SOL_DEPOSIT_ADDRESSES'))
    mock_sol_usd_rate: str = field(default_factory=lambda: os.getenv('CFS_MOCK_SOL_USD_RATE','150.00'))
    tron_rpc_url: str = field(default_factory=lambda: os.getenv('CFS_TRON_RPC_URL','https://api.trongrid.io').strip())
    tron_api_key: str = field(default_factory=lambda: os.getenv('CFS_TRON_API_KEY','').strip())
    bsc_rpc_url: str = field(default_factory=lambda: os.getenv('CFS_BSC_RPC_URL','https://bsc-dataseed.bnbchain.org').strip())
    solana_rpc_url: str = field(default_factory=lambda: os.getenv('CFS_SOLANA_RPC_URL','https://api.mainnet-beta.solana.com').strip())
    sol_price_url: str = field(default_factory=lambda: os.getenv('CFS_SOL_PRICE_URL','https://api.coingecko.com/api/v3/simple/price').strip())
    blockchain_timeout_seconds: float = field(default_factory=lambda: float(os.getenv('CFS_BLOCKCHAIN_TIMEOUT_SECONDS','10')))
    blockchain_retries: int = field(default_factory=lambda: int(os.getenv('CFS_BLOCKCHAIN_RETRIES','2')))
    tron_min_confirmations: int = field(default_factory=lambda: int(os.getenv('CFS_TRON_MIN_CONFIRMATIONS','20')))
    bsc_min_confirmations: int = field(default_factory=lambda: int(os.getenv('CFS_BSC_MIN_CONFIRMATIONS','5')))
    solana_commitment: str = field(default_factory=lambda: os.getenv('CFS_SOLANA_COMMITMENT','finalized').strip().lower())
    quote_seconds: int = 900
    order_seconds: int = 1800

    def __post_init__(self):
        self.database_path=Path(os.getenv('CFS_DATABASE_PATH',str(self.root/'database'/'cfs.db')))
        self.quarantine_dir=Path(os.getenv('CFS_QUARANTINE_DIR',str(self.root/'storage'/'quarantine')))
        self.published_dir=Path(os.getenv('CFS_PUBLISHED_DIR',str(self.root/'storage'/'published')))
        self.database_path.parent.mkdir(parents=True,exist_ok=True); self.quarantine_dir.mkdir(parents=True,exist_ok=True); self.published_dir.mkdir(parents=True,exist_ok=True)
        self.payments_mode=self.payments_mode.upper().strip()
        self.deposit_address_mode=self.deposit_address_mode.upper().strip()
        if self.environment not in {'development','test','production'}: raise RuntimeError('Invalid CFS_ENV')
        if self.storage_backend not in {'local','s3'}: raise RuntimeError('Invalid CFS_STORAGE_BACKEND')
        if self.payments_mode not in {'MOCK','TEST','PRODUCTION'}: raise RuntimeError('Invalid CFS_PAYMENTS_MODE')
        if self.deposit_address_mode not in {'EXCLUSIVE','SHARED_MARKER'}: raise RuntimeError('Invalid CFS_DEPOSIT_ADDRESS_MODE')
        if self.solana_commitment not in {'confirmed','finalized'}: raise RuntimeError('Invalid CFS_SOLANA_COMMITMENT')
        if self.tron_min_confirmations < 1 or self.bsc_min_confirmations < 1: raise RuntimeError('Blockchain confirmation counts must be positive')
        if self.blockchain_timeout_seconds <= 0: raise RuntimeError('Blockchain timeout must be positive')
        if self.blockchain_retries < 0 or self.blockchain_retries > 5: raise RuntimeError('Blockchain retries must be between 0 and 5')
        if self.environment=='production' and not self.owner_bootstrap_token: raise RuntimeError('Production requires CFS_OWNER_BOOTSTRAP_TOKEN')
        if self.environment=='production' and not self.database_url: raise RuntimeError('Production requires DATABASE_URL for persistent database storage')
        if self.environment=='production' and self.storage_backend=='local': raise RuntimeError('Production requires persistent object storage; set CFS_STORAGE_BACKEND=s3')
        if self.storage_backend=='s3':
            missing=[name for name,val in [('CFS_S3_ENDPOINT_URL',self.s3_endpoint_url),('CFS_S3_BUCKET',self.s3_bucket),('CFS_S3_ACCESS_KEY_ID',self.s3_access_key_id),('CFS_S3_SECRET_ACCESS_KEY',self.s3_secret_access_key)] if not val]
            if missing: raise RuntimeError('Missing S3 storage settings: '+','.join(missing))
        if self.payments_mode=='PRODUCTION' and not self.production_payments_enabled: raise RuntimeError('Production payments require CFS_PRODUCTION_PAYMENTS_ENABLED=true')
        if self.payments_mode=='PRODUCTION':
            missing=[name for name,val in [('CFS_TRON_RPC_URL',self.tron_rpc_url),('CFS_BSC_RPC_URL',self.bsc_rpc_url),('CFS_SOLANA_RPC_URL',self.solana_rpc_url),('CFS_SOL_PRICE_URL',self.sol_price_url)] if not val]
            if missing: raise RuntimeError('Missing production payment provider settings: '+','.join(missing))
