import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const alt = "ImpactFlow — MEAL operating system for development organizations";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpenGraphImage() {
  const logoBytes = await readFile(
    join(process.cwd(), "public", "brand", "impactflow-logo.png"),
  );
  const logoSrc = `data:image/png;base64,${logoBytes.toString("base64")}`;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background:
            "radial-gradient(circle at 30% 40%, #0f2a4a 0%, #081226 55%, #040810 100%)",
          color: "#f8fafc",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 48,
            padding: "0 72px",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={logoSrc}
            width={220}
            height={220}
            alt=""
            style={{ borderRadius: 48 }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div
              style={{
                fontSize: 72,
                fontWeight: 700,
                letterSpacing: "-0.03em",
                lineHeight: 1.05,
              }}
            >
              ImpactFlow
            </div>
            <div
              style={{
                fontSize: 28,
                color: "#94a3b8",
                maxWidth: 560,
                lineHeight: 1.35,
              }}
            >
              MEAL operating system for development organizations worldwide
            </div>
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
