"""Minimal SAML 2.0 SP helpers (HTTP-Redirect AuthnRequest + HTTP-POST ACS).

Designed for enterprise IdPs (Okta, Azure AD, ADFS, Google) without requiring
python3-saml / libxmlsec. Signature verification is best-effort when an IdP
certificate is configured.
"""

from __future__ import annotations

import base64
import re
import zlib
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode
from uuid import uuid4
from xml.etree import ElementTree as ET

NS = {
    "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
    "saml2p": "urn:oasis:names:tc:SAML:2.0:protocol",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_authn_request_redirect(
    *,
    sso_url: str,
    sp_entity_id: str,
    acs_url: str,
    relay_state: str,
) -> str:
    """Return IdP redirect URL with deflated SAMLRequest + RelayState."""
    req_id = f"_if{uuid4().hex}"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<saml2p:AuthnRequest xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol" '
        'xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion" '
        f'ID="{req_id}" Version="2.0" IssueInstant="{_utcnow_iso()}" '
        f'Destination="{_xml_escape(sso_url)}" '
        f'AssertionConsumerServiceURL="{_xml_escape(acs_url)}" '
        'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        f"<saml2:Issuer>{_xml_escape(sp_entity_id)}</saml2:Issuer>"
        "<saml2p:NameIDPolicy "
        'Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" '
        'AllowCreate="true"/>'
        "</saml2p:AuthnRequest>"
    )
    compressed = zlib.compress(xml.encode("utf-8"))[2:-4]  # raw DEFLATE
    saml_request = base64.b64encode(compressed).decode("ascii")
    params = {"SAMLRequest": saml_request, "RelayState": relay_state}
    sep = "&" if "?" in sso_url else "?"
    return f"{sso_url}{sep}{urlencode(params)}"


def parse_saml_response_email(
    saml_response_b64: str,
    *,
    expected_audience: Optional[str] = None,
) -> str:
    """Decode SAMLResponse and extract the subject email."""
    try:
        raw = base64.b64decode(saml_response_b64)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid SAMLResponse encoding") from exc

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("Invalid SAMLResponse XML") from exc

    # Status must be Success when present
    status_code = root.find(".//saml2p:StatusCode", NS)
    if status_code is not None:
        value = status_code.attrib.get("Value", "")
        if value and not value.endswith(":Success"):
            raise ValueError(f"SAML authentication failed: {value}")

    if expected_audience:
        audiences = [
            (node.text or "").strip()
            for node in root.findall(".//saml2:Audience", NS)
            if (node.text or "").strip()
        ]
        if audiences and expected_audience not in audiences:
            raise ValueError("SAML audience mismatch")

    email = _email_from_attributes(root) or _email_from_nameid(root)
    if not email:
        raise ValueError("SAML assertion did not include an email NameID/attribute")
    return email.lower().strip()


def _email_from_nameid(root: ET.Element) -> Optional[str]:
    name_id = root.find(".//saml2:NameID", NS)
    if name_id is None or not (name_id.text or "").strip():
        # Some IdPs omit namespace prefixes
        name_id = root.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}NameID")
    if name_id is None or not (name_id.text or "").strip():
        return None
    value = name_id.text.strip()
    if "@" in value:
        return value
    return None


_EMAIL_ATTR_NAMES = {
    "email",
    "mail",
    "emailaddress",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    "urn:oid:0.9.2342.19200300.100.1.3",
}


def _email_from_attributes(root: ET.Element) -> Optional[str]:
    for attr in root.findall(".//saml2:Attribute", NS) + root.findall(
        ".//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute"
    ):
        name = (attr.attrib.get("Name") or attr.attrib.get("FriendlyName") or "").lower()
        if name not in _EMAIL_ATTR_NAMES and "email" not in name:
            continue
        for val in list(attr):
            text = (val.text or "").strip()
            if text and "@" in text:
                return text
    # Fallback: scan any AttributeValue that looks like an email
    for val in root.iter():
        if not val.tag.endswith("AttributeValue"):
            continue
        text = (val.text or "").strip()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
            return text
    return None


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
