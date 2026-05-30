/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    "@langchain/langgraph-sdk",
    "@langchain/core",
    "@langchain/langgraph",
  ],
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
