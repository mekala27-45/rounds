import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "rounds | Health system analytics",
  description: "A department-by-department view of a synthetic health system. Explore measures, model evidence and data quality.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
