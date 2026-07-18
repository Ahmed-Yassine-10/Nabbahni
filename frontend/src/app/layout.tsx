import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Nabbahni — La météo des médicaments",
  description:
    "Plateforme nationale de prédiction des ruptures de médicaments en Tunisie.",
  icons: { icon: "/brand/mark.png", apple: "/brand/mark.png" },
};

// The [locale] segment owns <html>/<body> so it can set lang + dir per locale.
export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
