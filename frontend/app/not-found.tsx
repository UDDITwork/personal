import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <h1 className="text-6xl font-bold text-slate-900 mb-4">404</h1>
      <p className="text-xl text-slate-600 mb-8">Page not found</p>
      <Link
        href="/dashboard"
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
