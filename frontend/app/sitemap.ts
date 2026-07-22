import type { MetadataRoute } from "next";

const routes = [
  "",
  "/feed",
  "/insights",
  "/polls",
  "/search",
  "/saved",
  "/chat",
  "/trends",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `https://kampher.vercel.app${route}`,
    changeFrequency: route === "/polls" ? "monthly" : "daily",
    priority: route === "" ? 1 : 0.8,
  }));
}
