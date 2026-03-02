"use client";

import { useEffect, useState, type ReactNode } from "react";

interface PersonalizedProps {
  /** Unique element ID — the client script sends this to the backend */
  elementId: string;
  /** Fallback content shown before personalization loads */
  children: ReactNode;
  className?: string;
  as?: keyof HTMLElementTagNameMap;
}

/**
 * React wrapper for ABM-personalized elements.
 * Renders a `dummy-ops-element` attribute so abm.js can find and update it.
 * Also listens for the `abm:personalized` event for React state updates.
 *
 * Usage:
 *   <Personalized elementId="headline" as="h1">
 *     Default Headline
 *   </Personalized>
 */
export function Personalized({
  elementId,
  children,
  className,
  as: Tag = "span",
}: PersonalizedProps) {
  const [content, setContent] = useState<string | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.components?.[elementId]) {
        setContent(detail.components[elementId]);
      }
    };
    window.addEventListener("abm:personalized", handler);
    return () => window.removeEventListener("abm:personalized", handler);
  }, [elementId]);

  const Element = Tag as React.ElementType;

  return (
    <Element className={className} dummy-ops-element={elementId}>
      {content ?? children}
    </Element>
  );
}
