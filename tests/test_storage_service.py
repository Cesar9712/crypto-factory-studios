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

    def list_objects_v2(self, Bucket, Prefix, MaxKeys=1000, **kwargs):
        rows=[{'Key':k} for (b,k) in self.objects if b==Bucket and k.startswith(Prefix)]
        return {'Contents':rows[:MaxKeys], 'IsTruncated':False}

    def delete_objects(self, Bucket, Delete):
        for item in Delete.get('Objects',[]):
            self.delete_object(Bucket, item['Key'])
        return {'Deleted':Delete.get('Objects',[])}


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


def test_delete_game_removes_archives_and_published_prefix(monkeypatch):
    fake=FakeS3()
    monkeypatch.setattr(boto3, 'client', lambda *a, **kw: fake)
    storage=StorageService(settings())
    fake.objects[('bucket','quarantine/build-a.zip')]=b'zip'
    fake.objects[('bucket','published/game-a/build-a/index.html')]=b'<h1>A</h1>'
    fake.objects[('bucket','published/game-a/build-a/game.js')]=b'1'
    fake.objects[('bucket','published/game-b/build-b/index.html')]=b'<h1>B</h1>'
    storage.delete_game('game-a',['s3://bucket/quarantine/build-a.zip'])
    assert ('bucket','quarantine/build-a.zip') not in fake.objects
    assert not any(k.startswith('published/game-a/') for b,k in fake.objects if b=='bucket')
    assert ('bucket','published/game-b/build-b/index.html') in fake.objects
