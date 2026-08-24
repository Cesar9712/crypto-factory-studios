from __future__ import annotations
import hashlib, io, json, mimetypes, os, shutil, subprocess, tempfile, zipfile
from pathlib import Path, PurePosixPath
from dataclasses import dataclass

ALLOWED_EXTENSIONS={'.html','.htm','.js','.mjs','.wasm','.pck','.json','.css','.png','.jpg','.jpeg','.webp','.svg','.ico','.mp3','.ogg','.wav','.woff','.woff2','.ttf','.txt','.bin'}
EICAR_FRAGMENT=b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE'

@dataclass
class ScanResult:
    status:str; engine:str; details:str

class UploadSecurityService:
    def __init__(self,max_upload:int,max_uncompressed:int,max_files:int,max_ratio:float,antivirus_required:bool=False):
        self.max_upload=max_upload; self.max_uncompressed=max_uncompressed; self.max_files=max_files; self.max_ratio=max_ratio; self.antivirus_required=antivirus_required
    def validate_zip(self,data:bytes)->dict:
        if len(data)>self.max_upload: raise ValueError('upload_too_large')
        if not zipfile.is_zipfile(io.BytesIO(data)): raise ValueError('invalid_zip')
        total=0; count=0; entries=[]; has_index=False
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                count+=1
                if count>self.max_files: raise ValueError('too_many_files')
                p=PurePosixPath(info.filename.replace('\\','/'))
                if p.is_absolute() or '..' in p.parts: raise ValueError('path_traversal')
                if info.flag_bits & 0x1: raise ValueError('encrypted_archive')
                if info.is_dir(): continue
                total+=info.file_size
                if total>self.max_uncompressed: raise ValueError('archive_uncompressed_too_large')
                ratio=(info.file_size/max(info.compress_size,1)) if info.file_size else 1
                if ratio>self.max_ratio and info.file_size>1024*1024: raise ValueError('suspicious_compression_ratio')
                ext=Path(info.filename).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS: raise ValueError(f'file_type_not_allowed:{ext or "none"}')
                if p.name.lower()=='index.html': has_index=True
                entries.append({'path':str(p),'size':info.file_size,'compressed':info.compress_size})
        if not has_index: raise ValueError('missing_index_html')
        return {'file_count':count,'uncompressed_bytes':total,'entries':entries}
    def scan(self,data:bytes)->ScanResult:
        if EICAR_FRAGMENT in data: return ScanResult('MALICIOUS','built-in','EICAR test signature detected')
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.is_dir() or info.file_size > 8 * 1024 * 1024:
                        continue
                    with z.open(info) as entry:
                        if EICAR_FRAGMENT in entry.read():
                            return ScanResult('MALICIOUS','built-in','EICAR test signature detected in archive entry')
        except Exception:
            return ScanResult('FAILED_SCAN','built-in','Archive content scan failed')
        clamscan=shutil.which('clamscan') if self.antivirus_required else None
        if clamscan:
            with tempfile.NamedTemporaryFile(suffix='.zip',delete=False) as f:
                f.write(data); path=f.name
            try:
                p=subprocess.run([clamscan,'--no-summary',path],capture_output=True,text=True,timeout=60)
                if p.returncode==0: return ScanResult('CLEAN','ClamAV',p.stdout.strip() or 'clean')
                if p.returncode==1: return ScanResult('MALICIOUS','ClamAV',p.stdout.strip() or 'malware detected')
                return ScanResult('FAILED_SCAN','ClamAV',p.stderr.strip() or 'scanner error')
            finally: os.unlink(path)
        if self.antivirus_required: return ScanResult('FAILED_SCAN','none','Production antivirus is required but unavailable')
        return ScanResult('CLEAN','development-fallback','Structural validation passed; real AV unavailable in development')
    def safe_extract(self,data:bytes,destination:Path)->None:
        destination.mkdir(parents=True,exist_ok=True)
        root=destination.resolve()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                target=(destination/info.filename).resolve()
                if root not in target.parents and target!=root: raise ValueError('path_traversal')
                if info.is_dir(): target.mkdir(parents=True,exist_ok=True); continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src, open(target,'wb') as dst: shutil.copyfileobj(src,dst)
