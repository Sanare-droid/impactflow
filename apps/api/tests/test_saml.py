"""Unit tests for minimal SAML SP helpers."""

from __future__ import annotations

import base64

from app.services.saml import build_authn_request_redirect, parse_saml_response_email


def test_build_authn_request_redirect_contains_params():
    url = build_authn_request_redirect(
        sso_url="https://idp.example.com/sso",
        sp_entity_id="https://app.impactflow.test",
        acs_url="https://app.impactflow.test/sso/saml",
        relay_state="org-id:abc123",
    )
    assert url.startswith("https://idp.example.com/sso?")
    assert "SAMLRequest=" in url
    assert "RelayState=org-id%3Aabc123" in url or "RelayState=org-id:abc123" in url


def test_parse_saml_response_email_from_nameid():
    xml = """<?xml version="1.0"?>
    <saml2p:Response xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"
      xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">
      <saml2p:Status>
        <saml2p:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
      </saml2p:Status>
      <saml2:Assertion>
        <saml2:Conditions>
          <saml2:AudienceRestriction>
            <saml2:Audience>https://app.impactflow.test</saml2:Audience>
          </saml2:AudienceRestriction>
        </saml2:Conditions>
        <saml2:Subject>
          <saml2:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
            field.worker@example.com
          </saml2:NameID>
        </saml2:Subject>
      </saml2:Assertion>
    </saml2p:Response>
    """
    b64 = base64.b64encode(xml.encode()).decode()
    email = parse_saml_response_email(
        b64, expected_audience="https://app.impactflow.test"
    )
    assert email == "field.worker@example.com"
