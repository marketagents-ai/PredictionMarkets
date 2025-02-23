'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-zinc-800 p-6 rounded-lg max-w-lg w-full">
        <h2 className="text-xl font-bold text-red-400 mb-4">
          Something went wrong!
        </h2>
        <p className="text-zinc-300 mb-4">{error.message}</p>
        <button
          onClick={reset}
          className="bg-zinc-700 hover:bg-zinc-600 px-4 py-2 rounded"
        >
          Try again
        </button>
      </div>
    </div>
  )
}