import io, zipfile, pytest
from backend.app.upload_security import UploadSecurityService,EICAR_FRAGMENT

def make(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for n,d in files.items(): z.writestr(n,d)
    return b.getvalue()

def s(): return UploadSecurityService(10_000_000,20_000_000,100,20.0,False)
def test_valid_html_zip(): assert s().validate_zip(make({'index.html':b'ok'}))['file_count']==1
def test_encrypted_or_traversal_guard():
    with pytest.raises(ValueError,match='path_traversal'): s().validate_zip(make({'../../x.html':b'x','index.html':b'ok'}))
def test_disallowed_extension():
    with pytest.raises(ValueError,match='file_type_not_allowed'): s().validate_zip(make({'index.html':b'ok','evil.exe':b'MZ'}))
def test_eicar_detection_gate():
    r=s().scan(make({'index.html':b'ok','note.txt':EICAR_FRAGMENT})); assert r.status=='MALICIOUS'
