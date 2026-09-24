import pytest
import socket
from app.core.ssrf import validate_outbound_url, SSRFBlockedError, classify_ip

def _dns_available() -> bool:
    try:
        socket.getaddrinfo("www.virustotal.com", None)
        return True
    except socket.gaierror:
        return False


def test_localhost_blocked():
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("http://localhost/admin")


def test_loopback_ip_blocked():
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("http://127.0.0.1/metadata")


def test_private_range_blocked():
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("http://10.0.0.1/")


def test_link_local_blocked():
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("http://169.254.169.254/latest/meta-data/")


def test_non_http_scheme_blocked():
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("file:///etc/passwd")
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("gopher://internal:70/")


def test_allowlist_enforced():
    with pytest.raises(SSRFBlockedError):
        validate_outbound_url("https://example.com/", require_allowlist=True)

@pytest.mark.skipif(not _dns_available(), reason="requires network DNS resolution")
def test_known_provider_allowed():
    validate_outbound_url("https://www.virustotal.com/api/v3/ip_addresses/1.1.1.1", require_allowlist=True)

def test_classify_ip():
    assert classify_ip("10.0.0.1") == "PRIVATE"
    assert classify_ip("127.0.0.1") == "LOOPBACK"
    assert classify_ip("169.254.1.1") == "LINK_LOCAL"
    assert classify_ip("1.1.1.1") == "PUBLIC"
    assert classify_ip("not-an-ip") == "INVALID"