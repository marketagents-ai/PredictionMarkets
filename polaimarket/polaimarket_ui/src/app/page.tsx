'use client'
import { Layout } from '@/components/Layout'
import { PredictionMarket } from '@/components/PredictionMarket'
import { ErrorBoundary } from 'react-error-boundary'

function ErrorFallback({error}: {error: Error}) {
  return (
    <div className="text-center p-6 bg-red-900/20 rounded-lg">
      <h2 className="text-xl font-bold text-red-400">Something went wrong:</h2>
      <pre className="mt-2 text-sm text-red-300">{error.message}</pre>
    </div>
  )
}

export default function Home() {
  return (
    <Layout>
      <div className="max-w-6xl mx-auto p-4">
        <h1 className="text-2xl font-bold mb-6">AI Agent Prediction Markets</h1>
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <PredictionMarket />
        </ErrorBoundary>
      </div>
    </Layout>
  )
}