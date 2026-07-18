"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  Alert,
  CitizenAvailability,
  ExpiryAnalysis,
  PharmacyExpiry,
  Transfer,
  Forecast,
  Medication,
  MedicationBrief,
  ModelRun,
  NationalStockRow,
  Page,
  PharmacyNearby,
  StockAnalysis,
  Recommendation,
  RiskFeatureCollection,
  Shortage,
  ShortageDetail,
  Substitution,
} from "./types";

export interface Me {
  sub: string;
  email: string | null;
  roles: string[];
  pharmacy_id: string | null;
  governorate_id: string | null;
  supplier_id: string | null;
}

export interface StockRow {
  id: string;
  pharmacy_id: string;
  medication_id: string;
  quantity: number;
  min_threshold: number;
  recorded_at: string;
  medication: MedicationBrief | null;
  coverage_days: number | null;
}

export function useStockAnalysis() {
  return useQuery({
    queryKey: ["stock-analysis"],
    queryFn: () => api<StockAnalysis>("/api/v1/stock/analysis"),
    retry: false,
  });
}

export function useNationalStock() {
  return useQuery({
    queryKey: ["national-stock"],
    queryFn: () => api<NationalStockRow[]>("/api/v1/stock/national?limit=1000"),
    retry: false,
  });
}

export function useModelRuns() {
  return useQuery({
    queryKey: ["model-runs"],
    queryFn: () => api<ModelRun[]>("/api/v1/admin/model-runs?limit=100"),
    retry: false,
  });
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/api/v1/me"),
    retry: false,
  });
}

export function usePharmacyStock(pharmacyId?: string | null) {
  return useQuery({
    queryKey: ["pharmacy-stock", pharmacyId],
    queryFn: () => api<StockRow[]>(`/api/v1/stock/pharmacy/${pharmacyId}`),
    enabled: !!pharmacyId,
  });
}

export function useShortageMap() {
  return useQuery({
    queryKey: ["shortage-map"],
    queryFn: () => api<RiskFeatureCollection>("/api/v1/shortages/map"),
  });
}

export function useShortages(params: { severity?: string; governorate?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.severity) qs.set("severity", params.severity);
  if (params.governorate) qs.set("governorate", params.governorate);
  qs.set("page_size", "100");
  return useQuery({
    queryKey: ["shortages", params],
    queryFn: () => api<Page<Shortage>>(`/api/v1/shortages?${qs.toString()}`),
  });
}

export function useShortageDetail(id: string) {
  return useQuery({
    queryKey: ["shortage", id],
    queryFn: () => api<ShortageDetail>(`/api/v1/shortages/${id}`),
    enabled: !!id,
  });
}

export function useMedication(id: string) {
  return useQuery({
    queryKey: ["medication", id],
    queryFn: () => api<Medication>(`/api/v1/medications/${id}`),
    enabled: !!id,
  });
}

export function useForecasts(medication: string, governorate?: string) {
  const qs = new URLSearchParams({ medication });
  if (governorate) qs.set("governorate", governorate);
  return useQuery({
    queryKey: ["forecasts", medication, governorate],
    queryFn: () => api<Forecast[]>(`/api/v1/forecasts?${qs.toString()}`),
    enabled: !!medication,
  });
}

export function useRecommendations(status?: string) {
  const qs = new URLSearchParams({ page_size: "100" });
  if (status) qs.set("status", status);
  return useQuery({
    queryKey: ["recommendations", status],
    queryFn: () => api<Page<Recommendation>>(`/api/v1/recommendations?${qs.toString()}`),
  });
}

export function useRecommendationAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: "validate" | "reject" }) =>
      api<Recommendation>(`/api/v1/recommendations/${id}/${action}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recommendations"] }),
  });
}

export function useAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: () => api<Alert[]>("/api/v1/alerts?limit=100"),
  });
}

export function useSubstitutions(medicationId: string) {
  return useQuery({
    queryKey: ["substitutions", medicationId],
    queryFn: () => api<Substitution[]>(`/api/v1/medications/${medicationId}/substitutions`),
    enabled: !!medicationId,
  });
}

// ---- Public (citizen) ----
export function useCitizenSearch(q: string) {
  return useQuery({
    queryKey: ["citizen", q],
    queryFn: () => api<CitizenAvailability>(`/api/v1/citizen/availability?q=${encodeURIComponent(q)}`),
    enabled: q.length >= 2,
    retry: false,
  });
}

export function useNearbyPharmacies(lat: number, lon: number, medication?: string) {
  const qs = new URLSearchParams({ lat: String(lat), lon: String(lon), radius_km: "25" });
  if (medication) qs.set("medication", medication);
  return useQuery({
    queryKey: ["nearby", lat, lon, medication],
    queryFn: () => api<PharmacyNearby[]>(`/api/v1/pharmacies/nearby?${qs.toString()}`),
    enabled: Number.isFinite(lat) && Number.isFinite(lon),
  });
}

export function useMedicationsMap() {
  return useQuery({
    queryKey: ["medications-map"],
    queryFn: async () => {
      const page = await api<Page<Medication>>("/api/v1/medications?page_size=200");
      const map: Record<string, Medication> = {};
      for (const m of page.items) map[m.id] = m;
      return map;
    },
  });
}

export function useMedicationSearch(q: string) {
  return useQuery({
    queryKey: ["med-search", q],
    queryFn: () => api<Page<Medication>>(`/api/v1/medications?q=${encodeURIComponent(q)}&page_size=10`),
    enabled: q.length >= 2,
  });
}

// ── Expiry / waste ────────────────────────────────────────────────────────────

export function useExpiryAnalysis() {
  return useQuery({
    queryKey: ["expiry-analysis"],
    queryFn: () => api<ExpiryAnalysis>("/api/v1/expiry/analysis"),
    retry: false,
    // The national sweep walks every lot of every pharmacy; keep it cached.
    staleTime: 5 * 60_000,
  });
}

export function usePharmacyExpiry(pharmacyId?: string | null) {
  return useQuery({
    queryKey: ["pharmacy-expiry", pharmacyId],
    queryFn: () => api<PharmacyExpiry>(`/api/v1/expiry/pharmacy/${pharmacyId}`),
    enabled: !!pharmacyId,
    retry: false,
  });
}

export function useRedistribution() {
  return useQuery({
    queryKey: ["redistribution"],
    queryFn: () => api<Transfer[]>("/api/v1/expiry/redistribution?limit=60"),
    retry: false,
    staleTime: 5 * 60_000,
  });
}
