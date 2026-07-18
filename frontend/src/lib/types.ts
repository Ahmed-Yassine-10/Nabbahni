export type Severity = "green" | "yellow" | "orange" | "red" | "critical";
export type Availability = "available" | "tension" | "shortage";

export interface Medication {
  id: string;
  atc_code: string;
  dci: string;
  brand_name: string;
  form: string;
  dosage: string;
  unit: string;
  ddd_value: number | null;
  unit_price_tnd: number;
  is_essential: boolean;
  requires_prescription: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** Denormalized medication identity carried by every list payload. */
export interface MedicationBrief {
  id: string;
  brand_name: string;
  dci: string;
  atc_code: string;
  form: string;
  dosage: string;
  is_essential: boolean;
  unit_price_tnd: number;
}

export interface Shortage {
  id: string;
  medication_id: string;
  governorate_id: string | null;
  horizon_days: number;
  probability: number;
  severity: Severity;
  estimated_shortage_date: string | null;
  coverage_days: number | null;
  computed_at: string;
  medication: MedicationBrief | null;
  governorate_name: string | null;
}

export interface NationalStockRow {
  medication_id: string;
  brand_name: string;
  dci: string;
  quantity: number;
  coverage_days: number | null;
  recorded_at: string;
  is_essential: boolean;
  unit_price_tnd: number;
}

export interface StockAnalysisBucket {
  label: string;
  min_days: number;
  max_days: number | null;
  count: number;
  severity: Severity;
}

export interface StockAnalysis {
  total_medications: number;
  total_units: number;
  total_value_tnd: number;
  median_coverage_days: number;
  essential_at_risk: number;
  buckets: StockAnalysisBucket[];
  lowest_coverage: NationalStockRow[];
}

export interface ModelRun {
  id: string;
  model_family: string;
  model_type: string;
  horizon_days: number | null;
  metrics: Record<string, number> | null;
  is_champion: boolean;
  mlflow_run_id: string | null;
  trained_at: string | null;
}

export interface TopFactor {
  feature: string;
  value: number;
  shap: number;
  label_fr: string;
}

export interface Explanation {
  top_factors: TopFactor[];
  narrative_fr: string | null;
  narrative_ar: string | null;
}

export interface ShortageDetail extends Shortage {
  medication: Medication | null;
  explanation: Explanation | null;
}

export interface Forecast {
  id: string;
  medication_id: string;
  governorate_id: string | null;
  horizon_days: number;
  forecast_date: string;
  predicted_qty: number;
  ci_lower: number;
  ci_upper: number;
  trend: "rising" | "stable" | "falling";
}

export interface Recommendation {
  id: string;
  medication_id: string;
  rec_type: string;
  title_fr: string;
  detail_fr: string;
  confidence: number;
  financial_impact_tnd: number;
  expected_shortage_reduction_pct: number;
  suggested_quantity: number | null;
  status: "proposed" | "validated" | "rejected";
  validated_at: string | null;
  medication: MedicationBrief | null;
  governorate_name: string | null;
}

export interface Substitution {
  id: string;
  target: Medication;
  atc_match_level: number;
  equivalence: string;
  ddd_ratio: number | null;
  notes_fr: string | null;
  requires_pharmacist_validation: boolean;
}

export interface CitizenAvailability {
  medication: Medication;
  national_status: Availability;
  by_governorate: {
    governorate: string;
    availability: Availability;
    pharmacies_with_stock: number;
    total_pharmacies: number;
  }[];
  alternatives: Substitution[];
}

export interface PharmacyNearby {
  id: string;
  name: string;
  type: string;
  address: string | null;
  phone: string | null;
  distance_km: number;
  latitude: number;
  longitude: number;
  availability: Availability;
  quantity: number | null;
}

export interface RiskFeatureProperties {
  governorate_id: string;
  code: string;
  name_fr: string;
  name_ar: string;
  centroid: [number, number];
  /** Governorate-level level, derived from the SHARE of medications at risk. */
  severity: Severity;
  /** Worst single medication in the governorate — for drill-down. */
  max_severity: Severity;
  risk_ratio: number;
  color: string;
  at_risk_count: number;
  counts: Record<string, number>;
  total: number;
}

export interface RiskFeature {
  type: "Feature";
  geometry: { type: string; coordinates: unknown } | null;
  properties: RiskFeatureProperties;
}

export interface RiskFeatureCollection {
  type: "FeatureCollection";
  features: RiskFeature[];
}

export interface Alert {
  id: string;
  scope: string;
  governorate_id: string | null;
  medication_id: string | null;
  severity: Severity;
  title_fr: string;
  body_fr: string;
  created_at: string;
  acknowledged_at: string | null;
  medication: MedicationBrief | null;
  governorate_name: string | null;
}
