import hashlib
import os
import re

import pytest
from fastapi.testclient import TestClient

import todoapp.main as main
from todoapp.templating import STATIC_DIR, static_url, static_version

client = TestClient(main.app)


def test_page_links_static_files_with_content_version():
    html = client.get("/login").text

    expected = hashlib.sha256((STATIC_DIR / "js/base.js").read_bytes()).hexdigest()[:12]
    assert f"/static/js/base.js?v={expected}" in html
    # Every static link in the layout is versioned.
    assert re.findall(r'/static/[^"]+', html)
    assert all("?v=" in url for url in re.findall(r'/static/[^"]+', html))


def test_versioned_url_is_served():
    html = client.get("/login").text
    url = re.search(r'src="([^"]*/static/js/base\.js\?v=[^"]+)"', html).group(1)

    assert client.get(url).status_code == 200


def test_version_changes_when_file_changes(tmp_path):
    file = tmp_path / "app.js"
    file.write_text("console.log(1);")
    first = static_version(file)
    assert static_version(file) == first  # stable while unchanged

    file.write_text("console.log(2);")
    stat = file.stat()
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))  # force a new mtime

    assert static_version(file) != first


@pytest.mark.parametrize("path", ["js/missing.js", "../templating.py"])
def test_missing_or_outside_files_raise(path):
    context = {"request": None}  # never reached: the path check comes first
    with pytest.raises(FileNotFoundError):
        static_url(context, path)
