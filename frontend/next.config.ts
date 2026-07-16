import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // output: "standalone", // enable for Cloud Run container builds in later phase
};

export default nextConfig;
