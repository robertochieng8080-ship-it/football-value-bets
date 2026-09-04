import "./globals.css"
import { Inter, Space_Grotesk } from "next/font/google"
const inter = Inter({ subsets: ["latin"] })
const space = Space_Grotesk({ subsets: ["latin"], weight: ["500","700"] })

export const metadata = { title: "FOOTBALLVALUE.BETS", description: "Pro Value Bets - Edge >5%" }

export default function RootLayout({ children }) {
  return <html lang="en"><body className={`${inter.className} bg-[#050507] text-white antialiased`}>{children}</body></html>
  }
