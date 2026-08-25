import io
import stat
import zipfile

import pytest

from backend.app.upload_security import EICAR_FRAGMENT, UploadSecurityService


def make(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for n,d in files.items():
            z.writestr(n,d)
    return b.getvalue()


def duplicate_zip():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html',b'ok')
        z.writestr('INDEX.HTML',b'duplicate')
    return b.getvalue()


def symlink_zip():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html',b'ok')
        info=zipfile.ZipInfo('link.txt')
        info.create_system=3
        info.external_attr=(stat.S_IFLNK | 0o777) << 16
        z.writestr(info,'/etc/passwd')
    return b.getvalue()


def s():
    return UploadSecurityService(10_000_000,20_000_000,100,20.0,False)


def test_valid_html_zip():
    result=s().validate_zip(make({'index.html':b'ok'}))
    assert result['file_count']==1
    assert s().scan(make({'index.html':b'ok'})).engine=='built-in-static'


def test_encrypted_or_traversal_guard():
    with pytest.raises(ValueError,match='path_traversal'):
        s().validate_zip(make({'../../x.html':b'x','index.html':b'ok'}))


def test_disallowed_extension():
    with pytest.raises(ValueError,match='file_type_not_allowed'):
        s().validate_zip(make({'index.html':b'ok','evil.exe':b'MZ'}))


def test_duplicate_normalized_paths_rejected():
    with pytest.raises(ValueError,match='duplicate_path'):
        s().validate_zip(duplicate_zip())


def test_symlink_entry_rejected():
    with pytest.raises(ValueError,match='symlink_not_allowed'):
        s().validate_zip(symlink_zip())


def test_eicar_detection_gate():
    r=s().scan(make({'index.html':b'ok','note.txt':EICAR_FRAGMENT}))
    assert r.status=='MALICIOUS'


def test_required_external_antivirus_fails_closed_when_unavailable():
    scanner=UploadSecurityService(10_000_000,20_000_000,100,20.0,True)
    r=scanner.scan(make({'index.html':b'ok'}))
    assert r.status=='FAILED_SCAN'
