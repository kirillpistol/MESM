from mesm.ingest.official_web import discover_official_files


def test_discover_official_files_deduplicates_and_prefers_descriptive_title():
    page = "https://example.org/budget/"
    html = """
    <html><body>
      <a href="/files/app1.xlsx"><img alt="Excel"></a>
      <a href="/files/app1.xlsx">Приложение 1. Доходы бюджета</a>
      <a href="files/app2.xls">Приложение 2. Источники финансирования</a>
      <a href="notes.pdf">PDF</a>
    </body></html>
    """
    links = discover_official_files(html, page, (".xls", ".xlsx"))
    assert len(links) == 2
    assert links[0].url == "https://example.org/files/app1.xlsx"
    assert links[0].title == "Приложение 1. Доходы бюджета"
    assert links[1].extension == ".xls"
