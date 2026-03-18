import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "DataMind AI — Intelligent Data Platform",
  description: "Multi-agent AI platform for autonomous data analysis, ML, forecasting, and anomaly detection",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        {children}
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: { background: "#111827", border: "1px solid rgba(99,102,241,0.3)", color: "#f9fafb" },
          }}
        />
      </body>
    </html>
  );
}
