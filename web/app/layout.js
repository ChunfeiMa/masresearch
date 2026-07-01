import "./globals.css";

export const metadata = {
  title: "MASResearcher — Physical AI · Multi-Agent · Vision AI",
  description:
    "An hourly, multi-agent research feed for Physical AI, Multi-Agent Systems, and Vision AI.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
