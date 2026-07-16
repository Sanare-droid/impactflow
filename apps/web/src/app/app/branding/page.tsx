"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function BrandingPage() {
  const qc = useQueryClient();
  const [productName, setProductName] = useState("");
  const [tagline, setTagline] = useState("");
  const [primary, setPrimary] = useState("#0F766E");
  const [secondary, setSecondary] = useState("#44403C");
  const [accent, setAccent] = useState("#14B8A6");
  const [logoUrl, setLogoUrl] = useState("");
  const [customDomain, setCustomDomain] = useState("");
  const [supportEmail, setSupportEmail] = useState("");
  const [termsUrl, setTermsUrl] = useState("");
  const [privacyUrl, setPrivacyUrl] = useState("");
  const [footer, setFooter] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [hidePoweredBy, setHidePoweredBy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["branding"],
    queryFn: () => api.getBranding(),
  });

  useEffect(() => {
    if (!data) return;
    setProductName(data.product_name ?? "");
    setTagline(data.tagline ?? "");
    setPrimary(data.primary_color || "#0F766E");
    setSecondary(data.secondary_color || "#44403C");
    setAccent(data.accent_color || "#14B8A6");
    setLogoUrl(data.logo_url ?? "");
    setCustomDomain(data.custom_domain ?? "");
    setSupportEmail(data.support_email ?? "");
    const meta = data.metadata ?? {};
    setTermsUrl(typeof meta.terms_url === "string" ? meta.terms_url : "");
    setPrivacyUrl(typeof meta.privacy_url === "string" ? meta.privacy_url : "");
    setFooter(typeof meta.footer === "string" ? meta.footer : "");
    setEnabled(data.is_enabled);
    setHidePoweredBy(data.hide_powered_by);
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      api.updateBranding({
        product_name: productName || null,
        tagline: tagline || null,
        primary_color: primary,
        secondary_color: secondary,
        accent_color: accent,
        logo_url: logoUrl || null,
        custom_domain: customDomain || null,
        support_email: supportEmail || null,
        is_enabled: enabled,
        hide_powered_by: hidePoweredBy,
        metadata: {
          terms_url: termsUrl || null,
          privacy_url: privacyUrl || null,
          footer: footer || null,
          css_tokens: {
            "--brand-primary": primary,
            "--brand-secondary": secondary,
            "--brand-accent": accent,
          },
        },
      }),
    onSuccess: async () => {
      setError(null);
      await qc.invalidateQueries({ queryKey: ["branding"] });
      await qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">White label</h1>
        <p className="mt-2 text-stone-500">
          Brand the workspace with your product name, colors, and domain for partner rollouts.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardTitle>Branding settings</CardTitle>
          <CardDescription>
            Public branding is available at{" "}
            <code className="text-xs">/api/v1/public/branding/&#123;org-slug&#125;</code>.
          </CardDescription>
          {isLoading ? (
            <p className="mt-4 text-sm text-stone-400">Loading…</p>
          ) : (
            <form
              className="mt-4 grid gap-3 md:grid-cols-2"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                save.mutate();
              }}
            >
              <div>
                <Label htmlFor="product">Product name</Label>
                <Input
                  id="product"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="Acme Impact OS"
                />
              </div>
              <div>
                <Label htmlFor="tagline">Tagline</Label>
                <Input
                  id="tagline"
                  value={tagline}
                  onChange={(e) => setTagline(e.target.value)}
                  placeholder="Results that matter"
                />
              </div>
              <div>
                <Label htmlFor="primary">Primary color</Label>
                <Input
                  id="primary"
                  value={primary}
                  onChange={(e) => setPrimary(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="secondary">Secondary color</Label>
                <Input
                  id="secondary"
                  value={secondary}
                  onChange={(e) => setSecondary(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="accent">Accent color</Label>
                <Input id="accent" value={accent} onChange={(e) => setAccent(e.target.value)} />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="logo">Logo URL</Label>
                <Input id="logo" value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="domain">Custom domain</Label>
                <Input
                  id="domain"
                  value={customDomain}
                  onChange={(e) => setCustomDomain(e.target.value)}
                  placeholder="impact.acme.org"
                />
              </div>
              <div>
                <Label htmlFor="support">Support email</Label>
                <Input
                  id="support"
                  type="email"
                  value={supportEmail}
                  onChange={(e) => setSupportEmail(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="terms">Terms of Service URL</Label>
                <Input id="terms" value={termsUrl} onChange={(e) => setTermsUrl(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="privacy">Privacy Policy URL</Label>
                <Input
                  id="privacy"
                  value={privacyUrl}
                  onChange={(e) => setPrivacyUrl(e.target.value)}
                />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="footer">Footer / email branding</Label>
                <Input
                  id="footer"
                  value={footer}
                  onChange={(e) => setFooter(e.target.value)}
                  placeholder="© Your Organization"
                />
              </div>
              <label className="flex items-center gap-2 text-sm md:col-span-2">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                />
                Enable white-label branding
              </label>
              <label className="flex items-center gap-2 text-sm md:col-span-2">
                <input
                  type="checkbox"
                  checked={hidePoweredBy}
                  onChange={(e) => setHidePoweredBy(e.target.checked)}
                />
                Hide “Powered by ImpactFlow”
              </label>
              {error && <p className="md:col-span-2 text-sm text-rose-600">{error}</p>}
              <div className="md:col-span-2">
                <Button type="submit" disabled={save.isPending}>
                  {save.isPending ? "Saving…" : "Save branding"}
                </Button>
              </div>
            </form>
          )}
        </Card>

        <Card>
          <CardTitle>Preview</CardTitle>
          <div
            className="mt-4 overflow-hidden rounded-2xl border border-stone-200 dark:border-stone-800"
            style={{ borderTopColor: primary, borderTopWidth: 4 }}
          >
            <div className="bg-stone-50 p-5 dark:bg-stone-900">
              <div className="text-xs uppercase tracking-[0.16em]" style={{ color: primary }}>
                {productName || "Your product"}
              </div>
              <p className="mt-2 text-lg font-semibold" style={{ color: secondary }}>
                {tagline || "Sign in to continue"}
              </p>
              <div
                className="mt-4 h-9 rounded-lg"
                style={{ backgroundColor: primary, opacity: 0.9 }}
              />
              {!hidePoweredBy && (
                <p className="mt-4 text-[11px] text-stone-400">Powered by ImpactFlow AI</p>
              )}
              {footer && <p className="mt-2 text-[11px] text-stone-500">{footer}</p>}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
