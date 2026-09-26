import os

from app import static_assets


def test_asset_url_changes_with_content_even_when_file_metadata_matches(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(static_assets, "STATIC_DIR", tmp_path)
    asset = tmp_path / "editor.js"
    asset.write_text("old content")
    original_stat = asset.stat()
    old_url = static_assets.static_asset_url("editor.js")

    assert static_assets.static_asset_url("editor.js") == old_url

    asset.write_text("new content")
    os.utime(asset, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    assert static_assets.static_asset_url("editor.js") != old_url
