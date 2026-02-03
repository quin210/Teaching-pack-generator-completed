import { useState } from 'react';
import { apiService } from '../services/api';

interface LoginProps {
  onLogin: (email: string) => void;
  onSwitchToRegister?: () => void;
}

export default function Login({ onLogin, onSwitchToRegister }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await apiService.login(email, password);
      onLogin(email);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl border border-stone-200 p-8 shadow-sm">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-semibold text-zinc-800 mb-2">
              Teaching Pack Builder
            </h1>
            <p className="text-stone-600 text-sm">Sign in to continue</p>
          </div>

          {error && (
            <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-zinc-800 mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all"
                placeholder="teacher@example.com"
                required
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-zinc-800 mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all"
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </div>

            <div className="text-xs text-stone-500 bg-stone-50 p-3 rounded-lg">
              <p className="font-medium mb-1">Default account:</p>
              <p>📧 teacher@example.com / 🔑 teacher123</p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>

          {onSwitchToRegister && (
            <div className="mt-6 text-center">
              <p className="text-sm text-stone-600">
                Don't have an account?{' '}
                <button
                  onClick={onSwitchToRegister}
                  className="text-yellow-600 hover:text-yellow-700 font-medium transition-colors"
                >
                  Sign up
                </button>
              </p>
            </div>
          )}
          </form>
        </div>
      </div>
    </div>
  );
}
