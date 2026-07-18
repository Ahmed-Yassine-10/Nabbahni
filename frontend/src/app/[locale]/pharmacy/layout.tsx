"use client";

import { AppShell } from "@/components/app-shell";
import type { ReactNode } from "react";

// See cc/layout.tsx — the shell themes itself from the signed-in role.
export default function PharmacyLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
