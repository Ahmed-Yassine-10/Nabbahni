"use client";

import { Link } from "@/i18n/routing";
import { LocaleSwitcher } from "./locale-switcher";
import { Activity, LayoutDashboard } from "lucide-react";

export function CitizenHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white">
            <Activity className="h-4 w-4" />
          </div>
          <span className="font-bold">SentinelleRx</span>
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href="/cc"
            className="hidden items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 sm:flex"
          >
            <LayoutDashboard className="h-3.5 w-3.5" /> Espace Pro
          </Link>
          <LocaleSwitcher />
        </div>
      </div>
    </header>
  );
}
