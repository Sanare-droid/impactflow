import type { NextConfig } from "next";

// Docker / self-host uses standalone. Netlify's Next runtime does not —
// NETLIFY is set automatically on Netlify builds (also forced in netlify.toml).
const nextConfig: NextConfig = {
  ...(process.env.NETLIFY || process.env.VERCEL
    ? {}
    : { output: "standalone" as const }),
};

export default nextConfig;
