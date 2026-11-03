from scripts import data_report


def test_data_doc_matches_the_fact_files() -> None:
    assert data_report.main(["--check"]) == 0
