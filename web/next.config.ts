import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components wyłączone: strony czytające ciasteczka sesji (login, /panel)
  // muszą renderować się dynamicznie. Da się to pogodzić przez Suspense,
  // ale na tym etapie to niepotrzebna komplikacja.
  cacheComponents: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
