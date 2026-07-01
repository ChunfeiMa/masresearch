/**
 * Static export for GitHub Pages.
 * On project pages the site is served under /<repo>, so set
 * NEXT_PUBLIC_BASE_PATH=/MASResearcher at build time (the deploy workflow does this).
 * Locally it defaults to "" so `npm run build` + a static server work at root.
 */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

/** @type {import('next').NextConfig} */
module.exports = {
  output: "export",
  basePath,
  assetPrefix: basePath || undefined,
  images: { unoptimized: true },
  trailingSlash: true,
};
