import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-slate-950">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-900 dark:text-white mb-4">404</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">Page not found</p>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          Go Home
        </button>
      </div>
    </div>
  )
}
