from mesm.ingest.snapshot import (
    MANIFEST_REL,
    collect_files,
    file_digest,
    verify_manifest,
    write_manifest,
)


def _make_root(tmp_path):
    (tmp_path / "data/processed").mkdir(parents=True)
    (tmp_path / "data/reference").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "data/processed/a.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (tmp_path / "data/reference/r.csv").write_text("k\nv\n", encoding="utf-8")
    (tmp_path / "config/official_sources.json").write_text("{}", encoding="utf-8")
    # производный файл в снимок не входит
    (tmp_path / "data/processed/fiscal_reference_panel.csv").write_text("d\n", encoding="utf-8")
    return tmp_path


def test_collect_files_skips_derived_panel(tmp_path):
    root = _make_root(tmp_path)
    assert collect_files(root) == [
        "config/official_sources.json",
        "data/processed/a.csv",
        "data/reference/r.csv",
    ]


def test_digest_ignores_line_ending_style(tmp_path):
    lf = tmp_path / "lf.csv"
    crlf = tmp_path / "crlf.csv"
    lf.write_bytes(b"a,b\n1,2\n")
    crlf.write_bytes(b"a,b\r\n1,2\r\n")
    assert file_digest(lf) == file_digest(crlf)


def test_verify_detects_changed_missing_and_unlisted(tmp_path):
    root = _make_root(tmp_path)
    write_manifest(root)
    assert (root / MANIFEST_REL).exists()
    assert verify_manifest(root) == {"missing": [], "changed": [], "unlisted": []}

    (root / "data/processed/a.csv").write_text("x,y\n1,3\n", encoding="utf-8")
    (root / "data/reference/r.csv").unlink()
    (root / "data/processed/new.csv").write_text("n\n1\n", encoding="utf-8")
    report = verify_manifest(root)
    assert report["changed"] == ["data/processed/a.csv"]
    assert report["missing"] == ["data/reference/r.csv"]
    assert report["unlisted"] == ["data/processed/new.csv"]


def test_local_gitignored_artifacts_are_not_part_of_snapshot(tmp_path):
    root = _make_root(tmp_path)
    (root / "data/processed/sberindex_spending_monthly.csv").write_text("x\n1\n", encoding="utf-8")
    (root / "data/processed/public_aggregates.csv").write_text("x\n1\n", encoding="utf-8")
    assert "data/processed/sberindex_spending_monthly.csv" not in collect_files(root)
    assert "data/processed/public_aggregates.csv" not in collect_files(root)
