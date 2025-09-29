import "./globals.css";
export const metadata = {
  title: "Profile Bot Dashboard",
  description: "Study tracker admin dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="container">
        {children}
      </body>
    </html>
  );
}


