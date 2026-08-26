from __future__ import annotations

import io
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ALLOWED_EXTENSIONS={'.html','.htm','.js','.mjs','.wasm','.pck','.json','.css','.png','.jpg','.jpeg','.webp','.svg','.ico','.mp3','.ogg','.wav','.woff','.woff2','.ttf','.bin'}
EICAR_FRAGMENT=b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE'


@dataclass
class ScanResult:
    status:str
    engine:str
    details:str


class UploadSecurityService:
    def __init__(self,max_upload:int,max_uncompressed:int,max_files:int,max_ratio:float,antivirus_required:bool=False):
        self.max_upload=max_upload
        self.max_uncompressed=max_uncompressed
        self.max_files=max_files
        self.max_ratio=max_ratio
        self.antivirus_required=antivirus_required

    @staticmethod
    def _normalized_path(name:str)->PurePosixPath:
        normalized=name.replace('\\','/')
        if '\x00' in normalized or any(ord(ch)<32 for ch in normalized):
            raise ValueError('invalid_path')
        p=PurePosixPath(normalized)
        if not normalized or p.is_absolute() or '..' in p.parts or any(part in {'','.'} for part in p.parts):
            raise ValueError('path_traversal')
        return p

    @staticmethod
    def _is_symlink(info:zipfile.ZipInfo)->bool:
        mode=(info.external_attr>>16)&0xFFFF
        return stat.S_IFMT(mode)==stat.S_IFLNK

    def validate_zip(self,data:bytes)->dict:
        if len(data)>self.max_upload:
            raise ValueError('upload_too_large')
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError('invalid_zip')
        total=0
        count=0
        entries=[]
        has_root_index=False
        seen:set[str]=set()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                count+=1
                if count>self.max_files:
                    raise ValueError('too_many_files')
                p=self._normalized_path(info.filename)
                key=str(p).casefold()
                if key in seen:
                    raise ValueError('duplicate_path')
                seen.add(key)
                if info.flag_bits & 0x1:
                    raise ValueError('encrypted_archive')
                if self._is_symlink(info):
                    raise ValueError('symlink_not_allowed')
                if info.is_dir():
                    continue
                total+=info.file_size
                if total>self.max_uncompressed:
                    raise ValueError('archive_uncompressed_too_large')
                ratio=(info.file_size/max(info.compress_size,1)) if info.file_size else 1
                if ratio>self.max_ratio and info.file_size>1024*1024:
                    raise ValueError('suspicious_compression_ratio')
                ext=Path(str(p)).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    raise ValueError(f'file_type_not_allowed:{ext or "none"}')
                # The play endpoint serves /play/<slug>/ as the build root. Requiring
                # index.html at that exact root prevents a build from validating and
                # publishing successfully only to fail with asset_not_found at launch.
                if len(p.parts)==1 and p.name.lower()=='index.html':
                    has_root_index=True
                entries.append({'path':str(p),'size':info.file_size,'compressed':info.compress_size})
        if not has_root_index:
            raise ValueError('missing_root_index_html')
        return {'file_count':count,'uncompressed_bytes':total,'entries':entries}

    def scan(self,data:bytes)->ScanResult:
        if EICAR_FRAGMENT in data:
            return ScanResult('MALICIOUS','built-in-static','EICAR test signature detected')
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    carry=b''
                    with z.open(info) as entry:
                        while True:
                            chunk=entry.read(64*1024)
                            if not chunk:
                                break
                            probe=carry+chunk
                            if EICAR_FRAGMENT in probe:
                                return ScanResult('MALICIOUS','built-in-static','EICAR test signature detected in archive entry')
                            carry=probe[-(len(EICAR_FRAGMENT)-1):]
        except Exception:
            return ScanResult('FAILED_SCAN','built-in-static','Archive content scan failed')
        if self.antivirus_required:
            return ScanResult('FAILED_SCAN','built-in-static','External antivirus was required but is not available in this runtime')
        return ScanResult('CLEAN','built-in-static','Archive allowlist, limits, path checks and built-in signature scan passed')

    def safe_extract(self,data:bytes,destination:Path)->None:
        destination.mkdir(parents=True,exist_ok=True)
        root=destination.resolve()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                p=self._normalized_path(info.filename)
                if self._is_symlink(info):
                    raise ValueError('symlink_not_allowed')
                target=(destination/str(p)).resolve()
                if root not in target.parents and target!=root:
                    raise ValueError('path_traversal')
                if info.is_dir():
                    target.mkdir(parents=True,exist_ok=True)
                    continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src, open(target,'wb') as dst:
                    shutil.copyfileobj(src,dst)
