/** @type {import('next').NextConfig} */
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || 'http://localhost:8000';

module.exports = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${BACKEND_ORIGIN}/health`,
      },
      {
        source: '/verify/:path*',
        destination: `${BACKEND_ORIGIN}/verify/:path*`,
      },
    ];
  },
};
