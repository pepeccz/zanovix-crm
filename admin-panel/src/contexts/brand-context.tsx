"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

export type Perspective = "internal" | "client";

interface BrandContextValue {
  perspective: Perspective;
  role: string;
  setPerspective: (p: Perspective) => void;
}

const BrandContext = createContext<BrandContextValue | null>(null);

export function BrandProvider({ children }: { children: ReactNode }) {
  const [perspective, setPerspective] = useState<Perspective>("internal");

  // role is a future concern; hardcoded "admin" until SSR auth lands (slice 5).
  const role = "admin";

  return (
    <BrandContext.Provider value={{ perspective, role, setPerspective }}>
      {children}
    </BrandContext.Provider>
  );
}

export function useBrand(): BrandContextValue {
  const v = useContext(BrandContext);
  if (!v) throw new Error("useBrand must be used inside BrandProvider");
  return v;
}
