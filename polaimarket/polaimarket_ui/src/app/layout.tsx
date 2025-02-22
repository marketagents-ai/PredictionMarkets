import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Agent Prediction Markets',
  description: 'Simulation of AI agents trading in prediction markets',
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#18181B', // zinc-900
  icons: {
    icon: '/favicon.ico',
  }
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-900 text-white">
        {children}
      </body>
    </html>
  )
}