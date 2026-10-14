/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // Evita dobles montajes en dev para WebSockets y TradingView
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" } : {}),
};

module.exports = nextConfig;
