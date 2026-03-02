"use client";

import { useEffect, useState } from "react";

interface ABMData {
  visitor: {
    name?: string;
    company?: string;
    role?: string;
  } | null;
  components: Record<string, string>;
  cached: boolean;
}

/**
 * React hook that listens for ABM personalization events.
 * Returns the latest personalization data from abm.js.
 *
 * Usage:
 *   const { components, visitor } = useABM();
 *   return <h1>{components["hero-headline"] ?? "Default"}</h1>;
 */
export function useABM(): ABMData {
  const [data, setData] = useState<ABMData>({
    visitor: null,
    components: {},
    cached: false,
  });

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) {
        setData({
          visitor: detail.visitor ?? null,
          components: detail.components ?? {},
          cached: detail.cached ?? false,
        });
      }
    };
    window.addEventListener("abm:personalized", handler);
    return () => window.removeEventListener("abm:personalized", handler);
  }, []);

  return data;
}
