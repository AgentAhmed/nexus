import "./globals.css";

export const metadata = {
  title: "NEXUS — Enterprise Intelligence System",
  description: "Multi-Agent Enterprise Intelligence by Andromeda",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen antialiased">{children}</body>
    </html>
  );
}
