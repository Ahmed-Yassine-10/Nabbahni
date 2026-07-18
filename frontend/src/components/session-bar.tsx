"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { clearSession, devLogin, getRole, setSession } from "@/lib/api";
import { PORTALS, ROLE_LABELS, type Role } from "@/lib/roles";
import { UserCog, LogOut, ChevronDown } from "lucide-react";

const ROLE_ORDER: Role[] = [
  "pct_admin",
  "regional_authority",
  "hospital_pharmacist",
  "community_pharmacist",
  "supplier",
  "citizen",
];

/**
 * Development session control. In production this is replaced by the Keycloak
 * sign-in button (NextAuth); the API only honours /auth/dev-login while
 * Keycloak is disabled.
 *
 * Switching role does a full navigation to that role's home route, because the
 * portals differ in navigation and layout — not just in the data they show.
 */
export function SessionBar() {
  const [role, setRole] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const params = useParams();
  const locale = (params?.locale as string) ?? "fr";

  useEffect(() => setRole(getRole()), []);

  const login = async (r: string) => {
    setBusy(true);
    try {
      const { access_token, role: granted } = await devLogin(r);
      setSession(access_token, granted);
      const home = PORTALS[granted as Role]?.home ?? "/";
      // Hard navigation: the shell re-reads the role and re-themes on load.
      window.location.href = `/${locale}${home === "/" ? "" : home}`;
    } catch {
      setBusy(false);
    }
  };

  const logout = () => {
    clearSession();
    window.location.href = `/${locale}`;
  };

  if (role) {
    return (
      <div className="flex items-center gap-2">
        <span
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold"
          style={{
            backgroundColor: "var(--portal-accent-soft)",
            color: "var(--portal-accent)",
          }}
        >
          <UserCog aria-hidden className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">
            {ROLE_LABELS[role as Role] ?? role}
          </span>
        </span>
        <button
          onClick={logout}
          aria-label="Se déconnecter"
          className="cursor-pointer rounded-md border border-slate-200 p-1.5 text-slate-500 transition-colors duration-150 hover:bg-slate-50"
        >
          <LogOut aria-hidden className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <select
        disabled={busy}
        defaultValue=""
        aria-label="Choisir un profil de démonstration"
        onChange={(e) => e.target.value && login(e.target.value)}
        className="min-h-[2.25rem] cursor-pointer appearance-none rounded-md border border-slate-200 bg-white ps-3 pe-8 text-sm font-medium text-slate-700 transition-colors duration-150 hover:bg-slate-50 disabled:opacity-50"
      >
        <option value="" disabled>
          {busy ? "Connexion…" : "Se connecter (démo)"}
        </option>
        {ROLE_ORDER.map((r) => (
          <option key={r} value={r}>
            {ROLE_LABELS[r]}
          </option>
        ))}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute end-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
      />
    </div>
  );
}
