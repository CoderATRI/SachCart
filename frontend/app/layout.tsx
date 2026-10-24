import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SachCart - Autonomous Checkout-Truth Agent",
  description: "Reveal drip pricing, dark patterns under CCPA 2023, and real competitor price comparisons before you pay.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
