import { MetadataRoute } from "next";

const DISTRICTS = [
  "braga", "porto", "aveiro", "lisboa", "leiria", "coimbra", "viseu",
  "setubal", "santarem", "beja", "faro", "evora", "braganca",
  "castelo-branco", "guarda", "viana-do-castelo", "vila-real",
  "portalegre", "madeira", "acores",
];

const BASE = "https://rotadafesta.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${BASE}/login`, lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    { url: `${BASE}/submit`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
  ];

  const districtPages: MetadataRoute.Sitemap = DISTRICTS.map((d) => ({
    url: `${BASE}/jogos/${d}`,
    lastModified: now,
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));

  return [...staticPages, ...districtPages];
}
