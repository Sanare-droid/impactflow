"""Tests for Epic 5 executive analytics and donor reporting."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_executive_dashboard(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.get("/api/v1/executive/dashboard", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "portfolio_health" in body
    assert "score" in body["portfolio_health"]
    assert "kpis" in body
    assert "beneficiary_reach" in body["kpis"]
    assert "citations" in body
    assert "risk_heat" in body
    assert "ai_insights" in body


@pytest.mark.asyncio
async def test_portfolio_and_impact(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    portfolio = await client.get("/api/v1/executive/portfolio", headers=headers)
    assert portfolio.status_code == 200, portfolio.text
    assert "charts" in portfolio.json()
    assert "indicator_trends" in portfolio.json()

    impact = await client.get("/api/v1/executive/impact", headers=headers)
    assert impact.status_code == 200, impact.text
    assert "cost_per_beneficiary" in impact.json()


@pytest.mark.asyncio
async def test_compliance_and_risks(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    compliance = await client.get("/api/v1/executive/compliance", headers=headers)
    assert compliance.status_code == 200, compliance.text
    assert "summary" in compliance.json()
    assert "recommendations" in compliance.json()

    risks = await client.get("/api/v1/executive/risks", headers=headers)
    assert risks.status_code == 200, risks.text
    assert "items" in risks.json()


@pytest.mark.asyncio
async def test_report_templates_clone_and_build(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    listed = await client.get("/api/v1/report-templates", headers=headers)
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert any(t.get("code") == "usaid-style" for t in items)

    cloned = await client.post(
        "/api/v1/report-templates/clone",
        headers=headers,
        json={"code": "usaid-style", "name": "Our USAID Pack"},
    )
    assert cloned.status_code == 201, cloned.text
    assert cloned.json()["name"] == "Our USAID Pack"

    built = await client.post(
        "/api/v1/reports/build",
        headers=headers,
        json={
            "name": "Q2 Donor Report",
            "template_code": "usaid-style",
            "generate_narrative": True,
            "narrative_type": "donor",
            "save_version": True,
        },
    )
    assert built.status_code == 201, built.text
    report_id = built.json()["id"]
    assert built.json()["status"] == "draft"
    assert built.json()["sections"]

    versions = await client.get(f"/api/v1/reports/{report_id}/versions", headers=headers)
    assert versions.status_code == 200
    assert len(versions.json()["items"]) >= 1

    approved = await client.post(f"/api/v1/reports/{report_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_template_build_export_includes_sections(client: AsyncClient, org_a: dict):
    """Template builds without AI must still export a non-empty outline."""
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    built = await client.post(
        "/api/v1/reports/build",
        headers=headers,
        json={
            "name": "Outline Only Donor Report",
            "template_code": "usaid-style",
            "generate_narrative": False,
            "save_version": False,
        },
    )
    assert built.status_code == 201, built.text
    body = built.json()
    assert body["sections"]
    assert body["content"]
    assert "Executive Summary" in (body["content"] or "")

    report_id = body["id"]
    for fmt in ("markdown", "html", "docx", "csv", "xlsx"):
        res = await client.get(
            f"/api/v1/reports/{report_id}/export/download",
            headers=headers,
            params={"format": fmt},
        )
        assert res.status_code == 200, f"{fmt}: {res.text}"
        assert len(res.content) > 100
        if fmt == "markdown":
            text = res.content.decode("utf-8")
            assert "Executive Summary" in text
            assert "Intermediate Results" in text
        if fmt == "xlsx":
            # SpreadsheetML — Content-Disposition should use .xls
            cd = res.headers.get("content-disposition", "")
            assert ".xls" in cd or "excel" in (res.headers.get("content-type") or "").lower()


@pytest.mark.asyncio
async def test_report_export_formats(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "name": "Export Test",
            "report_type": "progress",
            "summary": "Summary",
            "content": "# Hello\n\nGrounded content.",
        },
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    for fmt in ("markdown", "html", "csv", "docx", "pptx", "xlsx"):
        res = await client.get(
            f"/api/v1/reports/{report_id}/export/download",
            headers=headers,
            params={"format": fmt},
        )
        assert res.status_code == 200, f"{fmt}: {res.text}"
        assert len(res.content) > 0


@pytest.mark.asyncio
async def test_report_export_pdf_is_a_real_pdf(client: AsyncClient, org_a: dict):
    """format=pdf must return an actual application/pdf binary, not HTML disguised as PDF."""
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    created = await client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "name": "PDF Export Test",
            "report_type": "progress",
            "summary": "Summary",
            "content": "# Hello\n\nGrounded content.",
        },
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    res = await client.get(
        f"/api/v1/reports/{report_id}/export/download",
        headers=headers,
        params={"format": "pdf"},
    )
    assert res.status_code == 200, res.text
    assert res.headers.get("content-type", "").startswith("application/pdf")
    assert res.content[:5] == b"%PDF-"
    cd = res.headers.get("content-disposition", "")
    assert cd.endswith('.pdf"')
    assert ".pdf.html" not in cd


@pytest.mark.asyncio
async def test_executive_brief(client: AsyncClient, org_a: dict):
    headers = auth_headers(org_a["access_token"], org_a["organization_id"])
    res = await client.post(
        "/api/v1/executive/briefs",
        headers=headers,
        json={"audience": "board", "save_as_report": True},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["narrative"]
    assert body["report"]
    assert body["report"]["report_type"] == "executive_brief"


@pytest.mark.asyncio
async def test_executive_tenant_isolation(client: AsyncClient, org_a: dict, org_b: dict):
    headers_a = auth_headers(org_a["access_token"], org_a["organization_id"])
    built = await client.post(
        "/api/v1/reports/build",
        headers=headers_a,
        json={"name": "Org A Only", "generate_narrative": False, "save_version": False},
    )
    report_id = built.json()["id"]

    headers_b = auth_headers(org_b["access_token"], org_b["organization_id"])
    res = await client.get(f"/api/v1/reports/{report_id}", headers=headers_b)
    assert res.status_code == 404
