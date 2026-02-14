'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <h1 className="text-4xl font-bold text-slate-900 mb-4">Something went wrong</h1>
      <p className="text-slate-600 mb-8">An unexpected error occurred. Please try again.</p>
      <button
        onClick={reset}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
      >
        Try Again
      </button>
    </div>
  );
}
