import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Kampher",
    short_name: "Kampher",
    description: "Evidence-backed product opportunity intelligence.",
    start_url: "/",
    display: "standalone",
    background_color: "#080a08",
    theme_color: "#bef264",
  };
}
