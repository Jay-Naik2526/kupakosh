/** @type {import('next').NextConfig} */
// KK_EXPORT=1 -> static site in ./out, served by the FastAPI backend on one address (for sharing / tunnels).
// Otherwise (dev on :3000) /api/* is proxied to the backend on :8010.
const exportMode = process.env.KK_EXPORT === "1";
const nextConfig = exportMode
  ? { output: "export", trailingSlash: true, images: { unoptimized: true } }
  : { async rewrites() { return [{ source: "/api/:path*", destination: "http://localhost:8010/api/:path*" }]; } };
export default nextConfig;
