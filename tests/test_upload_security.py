import io
import stat
import zipfile

import pytest

from backend.app.upload_security import EICAR_FRAGMENT, UploadSecurityService


def make(files):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for n,d in files.items(): z.writestr(n,d)
    return b.getvalue()


def duplicate_zip():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html',b'ok'); z.writestr('INDEX.HTML',b'duplicate')
    return b.getvalue()


def symlink_zip():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html',b'ok'); info=zipfile.ZipInfo('link.txt'); info.create_system=3; info.external_attr=(stat.S_IFLNK | 0o777) << 16; z.writestr(info,'/etc/passwd')
    return b.getvalue()


def s(): return UploadSecurityService(10_000_000,20_000_000,100,20.0,False)


def test_valid_html_zip():
    result=s().validate_zip(make({'index.html':b'ok'})); assert result['file_count']==1; assert result['normalized'] is False
    assert s().scan(make({'index.html':b'ok'})).engine=='built-in-static'


def test_single_folder_godot_export_is_normalized():
    result=s().validate_zip(make({'MyGame/index.html':b'ok','MyGame/game.js':b'js','MyGame/game.wasm':b'wasm','MyGame/game.pck':b'pck'}))
    assert result['strip_prefix']=='MyGame'; assert result['normalized'] is True; assert result['godot_detected'] is True


def test_arbitrary_single_folder_export_is_normalized():
    result=s().validate_zip(make({'release-123/index.html':b'ok','release-123/game.mjs':b'js','release-123/game.wasm':b'w'}))
    assert result['strip_prefix']=='release-123'


def test_multiple_possible_indexes_are_rejected():
    with pytest.raises(ValueError,match='ambiguous_index_html'):
        s().validate_zip(make({'one/index.html':b'1','two/index.html':b'2'}))


def test_files_outside_candidate_root_are_rejected():
    with pytest.raises(ValueError,match='ambiguous_build_root'):
        s().validate_zip(make({'export/index.html':b'ok','export/game.wasm':b'w','other/game.js':b'x'}))


def test_missing_index_is_actionable():
    with pytest.raises(ValueError,match='missing_index_html'):
        s().validate_zip(make({'game.wasm':b'w'}))


def test_encrypted_or_traversal_guard():
    with pytest.raises(ValueError,match='path_traversal'): s().validate_zip(make({'../../x.html':b'x','index.html':b'ok'}))


def test_disallowed_extension():
    with pytest.raises(ValueError,match='file_type_not_allowed'): s().validate_zip(make({'index.html':b'ok','evil.exe':b'MZ'}))


def test_duplicate_normalized_paths_rejected():
    with pytest.raises(ValueError,match='duplicate_path'): s().validate_zip(duplicate_zip())


def test_symlink_entry_rejected():
    with pytest.raises(ValueError,match='symlink_not_allowed'): s().validate_zip(symlink_zip())


def test_eicar_detection_gate():
    assert s().scan(make({'index.html':b'ok','note.txt':EICAR_FRAGMENT})).status=='MALICIOUS'


def test_required_external_antivirus_fails_closed_when_unavailable():
    assert UploadSecurityService(10_000_000,20_000_000,100,20.0,True).scan(make({'index.html':b'ok'})).status=='FAILED_SCAN'
