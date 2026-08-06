// Next.js configuration.
// TODO: add image domains, rewrites to the API, and security headers.

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone", // required for the slim Docker runtime image
};

export default nextConfig;
