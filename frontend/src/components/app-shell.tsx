"use client";

import Image from "next/image";
import { Link, usePathname } from "@/i18n/routing";
import { cn } from "@/lib/utils";
import { getRole } from "@/lib/api";
import { portalFor, type NavKey } from "@/lib/roles";
import { LocaleSwitcher } from "./locale-switcher";
import { SessionBar } from "./session-bar";
import {
  AlertTriangle,
  Boxes,
  Calculator,
  Brain,
  ClipboardList,
  LayoutDashboard,
  LogIn,
  Menu,
  Package,
  Repeat,
  ShoppingCart,
  Trash2,
  Truck,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

/** Every nav destination in the product, keyed so roles can select a subset. */
const NAV_REGISTRY: Record<NavKey, { href: string; label: string; icon: ReactNode }> = {
  "cc.overview": {
    href: "/cc",
    label: "Vue nationale",
    icon: <LayoutDashboard className="h-4 w-4" />,
  },
  "cc.shortages": {
    href: "/cc/shortages",
    label: "Risques de rupture",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
  "cc.stock": {
    href: "/cc/stock",
    label: "Analyse des stocks",
    icon: <Boxes className="h-4 w-4" />,
  },
  "cc.expiry": {
    href: "/cc/expiry",
    label: "Péremption & gaspillage",
    icon: <Trash2 className="h-4 w-4" />,
  },
  "cc.recommendations": {
    href: "/cc/recommendations",
    label: "Recommandations",
    icon: <ClipboardList className="h-4 w-4" />,
  },
  "cc.supplyChain": {
    href: "/cc/supply-chain",
    label: "Chaîne d'approvisionnement",
    icon: <Truck className="h-4 w-4" />,
  },
  "cc.models": {
    href: "/cc/models",
    label: "Modèles & explicabilité",
    icon: <Brain className="h-4 w-4" />,
  },
  "cc.alerts": {
    href: "/cc/alerts",
    label: "Alertes",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
  "ph.stock": {
    href: "/pharmacy",
    label: "Mon stock",
    icon: <Package className="h-4 w-4" />,
  },
  "ph.allocation": {
    href: "/pharmacy/allocation",
    label: "Quantités recommandées",
    icon: <Calculator className="h-4 w-4" />,
  },
  "ph.orders": {
    href: "/pharmacy/orders",
    label: "Commandes suggérées",
    icon: <ShoppingCart className="h-4 w-4" />,
  },
  "ph.substitutions": {
    href: "/pharmacy/substitutions",
    label: "Substitutions",
    icon: <Repeat className="h-4 w-4" />,
  },
};

/**
 * Application chrome shared by the staff portals.
 *
 * The shell reads the signed-in role and re-themes itself: accent colour,
 * portal name, mission line and the navigation set all change. That is what
 * makes a regional director's screen recognisably not a PCT admin's.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [role, setRole] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // localStorage is only readable after mount, so `role` is null on the first
  // render even when signed in. `ready` distinguishes "not loaded yet" from
  // "genuinely signed out" — without it the gate below flashes on every load.
  useEffect(() => {
    setRole(getRole());
    setReady(true);
  }, []);
  useEffect(() => setMobileOpen(false), [pathname]);

  const portal = portalFor(role);
  const nav = portal.nav.map((key) => ({ key, ...NAV_REGISTRY[key] }));

  return (
    <div
      className="flex min-h-screen"
      style={
        {
          "--portal-accent": portal.accent,
          "--portal-accent-soft": portal.accentSoft,
        } as React.CSSProperties
      }
    >
      <Sidebar
        portalName={portal.name}
        nav={nav}
        pathname={pathname}
        className="hidden lg:flex"
      />

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Fermer le menu"
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMobileOpen(false)}
          />
          <Sidebar
            portalName={portal.name}
            nav={nav}
            pathname={pathname}
            className="relative z-10 flex h-full"
            onClose={() => setMobileOpen(false)}
          />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 py-2.5 backdrop-blur">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              aria-label="Ouvrir le menu"
              onClick={() => setMobileOpen(true)}
              className="cursor-pointer rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-800">
                {portal.name}
              </div>
              <div className="truncate text-2xs text-slate-500">{portal.mission}</div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <LocaleSwitcher />
            <SessionBar />
          </div>
        </header>

        <main className="flex-1 overflow-auto bg-slate-100 p-4">
          <div
            className={cn(
              "animate-fade-in mx-auto",
              portal.density === "dense" ? "max-w-[1600px]" : "max-w-6xl"
            )}
          >
            {ready && !role ? <SignInGate /> : children}
          </div>
        </main>
      </div>
    </div>
  );
}

/**
 * Shown on staff routes when nobody is signed in. Without this the page
 * renders its panels with zeroed KPIs and empty tables, which is
 * indistinguishable from "the platform has no data".
 */
function SignInGate() {
  return (
    <div className="mx-auto mt-10 max-w-lg rounded-lg border border-slate-200 bg-white p-8 text-center shadow-card">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
        <LogIn aria-hidden className="h-5 w-5 text-slate-500" />
      </div>
      <h1 className="text-lg font-semibold text-slate-900">Connexion requise</h1>
      <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-slate-600">
        Ces écrans sont réservés aux profils professionnels. Choisissez un profil
        de démonstration dans le menu <strong>« Se connecter (démo) »</strong> en
        haut à droite — chaque profil ouvre son propre portail.
      </p>
      <p className="mt-4 text-xs text-slate-400">
        L&apos;espace citoyen, lui, est accessible sans connexion.
      </p>
    </div>
  );
}

function Sidebar({
  portalName,
  nav,
  pathname,
  className,
  onClose,
}: {
  portalName: string;
  nav: { key: string; href: string; label: string; icon: ReactNode }[];
  pathname: string;
  className?: string;
  onClose?: () => void;
}) {
  return (
    <aside
      className={cn(
        "w-64 shrink-0 flex-col border-e border-slate-200 bg-white",
        className
      )}
    >
      <div className="flex items-center gap-2.5 border-b border-slate-100 px-4 py-3.5">
        <div className="min-w-0 flex-1">
          {/* Wordmark without the tagline: at sidebar size the strapline is an
              illegible smudge, and the portal name below already subtitles it. */}
          <Image
            src="/brand/wordmark.png"
            alt="Nabbahni"
            width={560}
            height={150}
            priority
            className="h-6 w-auto"
          />
          <div className="mt-1 truncate text-2xs text-slate-400">{portalName}</div>
        </div>
        {onClose && (
          <button
            type="button"
            aria-label="Fermer"
            onClick={onClose}
            className="cursor-pointer rounded p-1 text-slate-400 hover:bg-slate-100"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {nav.length === 0 && (
          <p className="px-3 py-4 text-xs text-slate-400">
            Aucun module pour ce profil.
          </p>
        )}
        {nav.map((item) => {
          // Exact match for index routes, prefix match for sections — otherwise
          // "/cc" would stay highlighted on every child page.
          const active =
            pathname === item.href ||
            (item.href !== "/cc" &&
              item.href !== "/pharmacy" &&
              pathname.startsWith(item.href + "/"));
          return (
            <Link
              key={item.key}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150",
                active ? "font-semibold" : "text-slate-600 hover:bg-slate-50"
              )}
              style={
                active
                  ? {
                      backgroundColor: "var(--portal-accent-soft)",
                      color: "var(--portal-accent)",
                    }
                  : undefined
              }
            >
              {item.icon}
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-100 px-4 py-3">
        <p className="text-2xs leading-relaxed text-slate-400">
          Aide à la décision. Toute action est validée par un pharmacien ou un
          officier PCT.
        </p>
      </div>
    </aside>
  );
}
