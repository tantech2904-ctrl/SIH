from app.parsers.registry import get_registry


def test_registry_loads_all_parsers():
    reg = get_registry()
    ids = set(reg.list_metadata().keys())
    assert {"rfc5424", "cef", "leef", "json", "jsonl", "xml", "csv"}.issubset(ids)


def test_cef_detection_and_parse():
    raw = ("CEF:0|Vendor|Prod|1.0|4625|Failed Logon|7|"
           "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=administrator outcome=failure")
    reg = get_registry()
    parser = reg.get("cef")
    det = parser.detect(raw)
    assert det.format == "CEF"
    assert det.confidence >= 0.9
    pr = parser.parse(raw)
    assert pr.success
    assert pr.fields["vendor"] == "Vendor"
    assert pr.fields["src"] == "203.0.113.5"
    assert pr.fields["suser"] == "administrator"
    assert pr.fields["outcome"] == "failure"


def test_leef_detection_and_parse():
    raw = ("LEEF:1.0|IBM|QRadar|2.0|1234|"
           "devTime=2026-01-15T10:30:00Z\tsrc=192.0.2.10\tdst=10.0.0.5\tseverity=8")
    parser = get_registry().get("leef")
    det = parser.detect(raw)
    assert det.format == "LEEF"
    assert det.confidence >= 0.9
    pr = parser.parse(raw)
    assert pr.success
    assert pr.fields["vendor"] == "IBM"
    assert pr.fields["src"] == "192.0.2.10"
    assert pr.fields["severity"] == "8"


def test_rfc5424_detection_and_parse():
    raw = "<34>1 2026-01-15T10:22:03.123Z host app 123 ID47 - Failed password for admin"
    parser = get_registry().get("rfc5424")
    det = parser.detect(raw)
    assert det.format == "RFC5424"
    assert det.confidence >= 0.9
    pr = parser.parse(raw)
    assert pr.success
    assert pr.fields["hostname"] == "host"
    assert pr.fields["app_name"] == "app"
    assert "Failed password" in pr.fields["message"]


def test_json_detection_and_parse():
    raw = '{"@timestamp":"2026-01-15T10:40:00Z","user":"alice","src_ip":"10.0.0.1"}'
    parser = get_registry().get("json")
    det = parser.detect(raw)
    assert det.format == "JSON"
    assert det.confidence > 0.9
    pr = parser.parse(raw)
    assert pr.success
    assert pr.fields["user"] == "alice"


def test_jsonl_detection():
    raw = '{"a":1}\n{"a":2}\n{"a":3}'
    parser = get_registry().get("jsonl")
    det = parser.detect(raw)
    assert det.format == "JSONL"
    assert det.confidence >= 0.8


def test_xml_detection_and_parse():
    raw = '<?xml version="1.0"?><Event><src_ip>1.2.3.4</src_ip></Event>'
    parser = get_registry().get("xml")
    det = parser.detect(raw)
    assert det.format == "XML"
    pr = parser.parse(raw)
    assert pr.success
    assert pr.fields["root"] == "Event"


def test_csv_detection_and_parse():
    raw = "src_ip,dst_ip,action\n1.2.3.4,5.6.7.8,allow\n"
    parser = get_registry().get("csv")
    det = parser.detect(raw)
    assert det.format == "CSV"
    assert det.confidence >= 0.7
    pr = parser.parse(raw)
    assert pr.success
    assert pr.fields["src_ip"] == "1.2.3.4"
    assert pr.fields["action"] == "allow"


def test_unknown_format_low_confidence():
    raw = "some completely unstructured line with no recognizable format"
    parser = get_registry().get("cef")
    det = parser.detect(raw)
    assert det.confidence < 0.3


def test_best_match_prefers_specific_parser():
    raw = ("CEF:0|Vendor|Prod|1.0|4625|Failed Logon|7|"
           "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=admin")
    parser, det = get_registry().best_match(raw)
    assert det.format == "CEF"
    assert parser.parser_id == "cef"