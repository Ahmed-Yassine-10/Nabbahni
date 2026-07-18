"use client";

import { AppShell } from "@/components/app-shell";
import type { ReactNode } from "react";

// Navigation and theming are derived from the signed-in role inside AppShell,
// so the layout itself carries no portal configuration.
export default function CommandCenterLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
