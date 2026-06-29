import type { ReactNode } from "react";

export const metadata = {
  title: "BotThisSite: Vercel BotID Challenge",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
