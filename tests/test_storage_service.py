import io
from types import SimpleNamespace

import boto3

from backend.app.storage import StorageService


class FakeS3:
    def __init__(self, fail=False):
        self.fail=fail
        self.objects={}
        self.deleted=[]

    def head_bucket(self, **kwargs):
        if self.fail:
            raise RuntimeError('unavailable')
        return {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        if self.fail:
            raise RuntimeError('unavailable')
        self.objects[(Bucket, Key)] = bytes(Body)
        return {}

    def get_object(self, Bucket, Key):
        if self.fail:
            raise RuntimeError('unavailable')
        return {'Body': io.BytesIO(self.objects[(Bucket, Key)]), 'ContentType': 'application/octet-stream'}

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))
        self.objects.pop((Bucket, Key), None)
        return {}


def settings():
    return SimpleNamespace(
        storage_backend='s3',
        s3_endpoint_url='https://example.invalid',
        s3_region='us-test-1',
        s3_access_key_id='test',
        s3_secret_access_key='test',
        s3_bucket='bucket',
    )


def test_s3_startup_verifies_read_write_and_cleanup(monkeypatch):
    fake=FakeS3()
    monkeypatch.setattr(boto3, 'client', lambda *a, **kw: fake)
    storage=StorageService(settings())
    assert storage.ping() is True
    assert fake.objects == {}
    assert len(fake.deleted) == 1


def test_s3_readiness_fails_when_storage_unavailable(monkeypatch):
    fake=FakeS3(fail=True)
    monkeypatch.setattr(boto3, 'client', lambda *a, **kw: fake)
    storage=StorageService(settings())
    assert storage.ping() is False
