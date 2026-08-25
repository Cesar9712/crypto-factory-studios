from __future__ import annotations
import io, mimetypes, secrets, zipfile
from pathlib import Path, PurePosixPath

class StorageService:
    def __init__(self, settings):
        self.settings=settings
        self.backend=settings.storage_backend
        self.client=None
        self._startup_verified=True
        if self.backend=='s3':
            import boto3
            self.client=boto3.client('s3',endpoint_url=settings.s3_endpoint_url,region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key_id,aws_secret_access_key=settings.s3_secret_access_key)
            self._startup_verified=self._verify_s3_read_write()

    def _verify_s3_read_write(self)->bool:
        key=f'_cfs_health/{secrets.token_hex(8)}.probe'
        payload=b'cfs-storage-read-write-check'
        try:
            self.client.head_bucket(Bucket=self.settings.s3_bucket)
            self.client.put_object(Bucket=self.settings.s3_bucket,Key=key,Body=payload,ContentType='application/octet-stream')
            obj=self.client.get_object(Bucket=self.settings.s3_bucket,Key=key)
            if obj['Body'].read()!=payload: return False
            return True
        except Exception:
            return False
        finally:
            try:
                self.client.delete_object(Bucket=self.settings.s3_bucket,Key=key)
            except Exception:
                pass

    def store_archive(self, build_id:str, data:bytes)->str:
        if self.backend=='local':
            p=self.settings.quarantine_dir/f'{build_id}.zip'; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data); return str(p)
        key=f'quarantine/{build_id}.zip'
        self.client.put_object(Bucket=self.settings.s3_bucket,Key=key,Body=data,ContentType='application/zip')
        return f's3://{self.settings.s3_bucket}/{key}'

    def read_archive(self, ref:str)->bytes:
        if not ref.startswith('s3://'): return Path(ref).read_bytes()
        key=ref.split('/',3)[3]
        return self.client.get_object(Bucket=self.settings.s3_bucket,Key=key)['Body'].read()

    def publish_zip(self, game_id:str, build_id:str, data:bytes, scanner)->None:
        if self.backend=='local':
            scanner.safe_extract(data,self.settings.published_dir/game_id/build_id); return
        root=f'published/{game_id}/{build_id}/'
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir(): continue
                p=PurePosixPath(info.filename.replace('\\','/'))
                if p.is_absolute() or '..' in p.parts: raise ValueError('path_traversal')
                body=z.read(info)
                ctype=mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
                self.client.put_object(Bucket=self.settings.s3_bucket,Key=root+str(p),Body=body,ContentType=ctype,CacheControl='public,max-age=300')

    def get_published(self, game_id:str, build_id:str, asset_path:str):
        p=PurePosixPath((asset_path or 'index.html').replace('\\','/'))
        if p.is_absolute() or '..' in p.parts: raise ValueError('invalid_path')
        if self.backend=='local':
            root=(self.settings.published_dir/game_id/build_id).resolve(); target=(root/str(p)).resolve()
            if root not in target.parents and target!=root: raise ValueError('invalid_path')
            if target.is_dir(): target=target/'index.html'
            if not target.is_file(): return None
            return target.read_bytes(), mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        key=f'published/{game_id}/{build_id}/{p}'
        try:
            obj=self.client.get_object(Bucket=self.settings.s3_bucket,Key=key)
        except Exception as exc:
            code=getattr(exc,'response',{}).get('Error',{}).get('Code','')
            if code in {'NoSuchKey','404','NotFound'}: return None
            raise
        return obj['Body'].read(), obj.get('ContentType') or mimetypes.guess_type(str(p))[0] or 'application/octet-stream'

    def ping(self)->bool:
        if self.backend=='local': return True
        if not self._startup_verified: return False
        try:
            self.client.head_bucket(Bucket=self.settings.s3_bucket); return True
        except Exception: return False
