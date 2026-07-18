/**
 * Role → portal mapping.
 *
 * The six user types don't just see different data behind the same chrome —
 * they get a different landing page, navigation, density and accent colour.
 * A PCT administrator opens a national command centre; a community pharmacist
 * opens a stock desk; a citizen opens a search box. This module is the single
 * place that decides which.
 */

export type Role =
  | "pct_admin"
  | "regional_authority"
  | "hospital_pharmacist"
  | "community_pharmacist"
  | "supplier"
  | "citizen";

export interface PortalDefinition {
  /** Landing route after sign-in. */
  home: string;
  /** Portal name shown under the wordmark. */
  name: string;
  /** One-line description of this user's job, shown in the header. */
  mission: string;
  /** Chrome accent (CSS colour) — distinguishes portals at a glance. */
  accent: string;
  accentSoft: string;
  /** Which nav groups this role may see. */
  nav: NavKey[];
  /** Dense = analyst tooling; comfortable = task-focused; public = citizen. */
  density: "dense" | "comfortable" | "public";
}

export type NavKey =
  | "cc.overview"
  | "cc.shortages"
  | "cc.stock"
  | "cc.expiry"
  | "cc.recommendations"
  | "cc.supplyChain"
  | "cc.models"
  | "cc.alerts"
  | "ph.stock"
  | "ph.orders"
  | "ph.allocation"
  | "ph.substitutions";

const NATIONAL_NAV: NavKey[] = [
  "cc.overview",
  "cc.shortages",
  "cc.stock",
  "cc.expiry",
  "cc.recommendations",
  "cc.supplyChain",
  "cc.models",
  "cc.alerts",
];

export const PORTALS: Record<Role, PortalDefinition> = {
  pct_admin: {
    home: "/cc",
    name: "Centre de commandement national",
    mission: "Pilotage national de l'approvisionnement",
    accent: "#1e40af",
    accentSoft: "#eff6ff",
    nav: NATIONAL_NAV,
    density: "dense",
  },
  regional_authority: {
    home: "/cc",
    name: "Direction régionale de la santé",
    mission: "Surveillance et arbitrage régional",
    accent: "#6d28d9",
    accentSoft: "#f5f3ff",
    // No model governance: regions consume predictions, they don't own them.
    nav: [
      "cc.overview",
      "cc.shortages",
      "cc.stock",
      "cc.expiry",
      "cc.recommendations",
      "cc.alerts",
    ],
    density: "dense",
  },
  hospital_pharmacist: {
    home: "/pharmacy",
    name: "Pharmacie hospitalière",
    mission: "Stock hospitalier et substitutions",
    accent: "#0f766e",
    accentSoft: "#f0fdfa",
    nav: ["ph.stock", "ph.allocation", "ph.orders", "ph.substitutions"],
    density: "comfortable",
  },
  community_pharmacist: {
    home: "/pharmacy",
    name: "Pharmacie d'officine",
    mission: "Stock, commandes et alternatives",
    accent: "#047857",
    accentSoft: "#ecfdf5",
    nav: ["ph.stock", "ph.allocation", "ph.orders", "ph.substitutions"],
    density: "comfortable",
  },
  supplier: {
    home: "/cc/supply-chain",
    name: "Espace fournisseur",
    mission: "Engagements de livraison et demande prévue",
    accent: "#b45309",
    accentSoft: "#fffbeb",
    nav: ["cc.supplyChain", "cc.alerts"],
    density: "comfortable",
  },
  citizen: {
    home: "/",
    name: "Espace citoyen",
    mission: "Trouver un médicament près de chez vous",
    accent: "#0369a1",
    accentSoft: "#f0f9ff",
    nav: [],
    density: "public",
  },
};

export const ROLE_LABELS: Record<Role, string> = {
  pct_admin: "Admin PCT",
  regional_authority: "Autorité régionale",
  hospital_pharmacist: "Pharmacien hospitalier",
  community_pharmacist: "Pharmacien d'officine",
  supplier: "Fournisseur",
  citizen: "Citoyen",
};

export function portalFor(role: string | null | undefined): PortalDefinition {
  if (role && role in PORTALS) return PORTALS[role as Role];
  return PORTALS.citizen;
}

export function isStaff(role: string | null | undefined): boolean {
  return role === "pct_admin" || role === "regional_authority";
}
