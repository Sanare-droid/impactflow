import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * SAML Assertion Consumer Service (HTTP-POST binding).
 * IdPs POST SAMLResponse here; we exchange with the API and hand tokens to the SPA.
 */
export async function POST(req: NextRequest) {
  const form = await req.formData();
  const samlResponse = form.get("SAMLResponse");
  const relayState = form.get("RelayState") ?? "";
  if (typeof samlResponse !== "string" || !samlResponse) {
    return NextResponse.redirect(
      new URL("/sso/callback?error=missing_saml_response", req.url),
      303,
    );
  }

  const body = new URLSearchParams();
  body.set("SAMLResponse", samlResponse);
  body.set("RelayState", String(relayState));

  const res = await fetch(`${API_URL}/api/v1/auth/sso/saml/acs`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    let message = "SAML login failed";
    try {
      const err = (await res.json()) as { message?: string; detail?: string };
      message = err.message || err.detail || message;
    } catch {
      /* ignore */
    }
    const dest = new URL("/sso/callback", req.url);
    dest.searchParams.set("error", message);
    return NextResponse.redirect(dest, 303);
  }

  const tokens = (await res.json()) as {
    access_token: string;
    refresh_token: string;
    organization_id?: string;
  };
  // Location headers cannot carry URL fragments reliably — hand off via a tiny HTML bridge.
  const frag = new URLSearchParams({
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    organization_id: tokens.organization_id ?? "",
  }).toString();
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>SSO</title></head>
<body><p>Completing sign-in…</p>
<script>location.replace(${JSON.stringify(`/sso/callback#${frag}`)});</script>
</body></html>`;
  return new NextResponse(html, {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}
