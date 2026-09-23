/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // Evita dobles montajes en dev para WebSockets y TradingView
  output: "standalone",
};

module.exports = nextConfig;
