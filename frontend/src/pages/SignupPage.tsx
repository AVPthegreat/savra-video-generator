import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api/api';

const SignupPage: React.FC = () => {
  const [formData, setFormData] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/auth/signup', formData);
      setSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: any) {
      let msg = 'Signup failed';
      if (err.response?.status === 422) {
        const detail = err.response.data.detail;
        msg = Array.isArray(detail) 
          ? detail.map((d: any) => d.msg).join(', ') 
          : detail;
      } else {
        msg = err.response?.data?.detail || msg;
      }
      setError(msg);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black text-white px-4">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Request Sent!</h1>
          <p className="text-zinc-400">Your application is now on the waitlist. We will notify you once approved.</p>
          <p className="mt-4 text-sm text-zinc-600">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white px-4">
      <div className="w-full max-w-md p-8 bg-zinc-900 rounded-2xl border border-zinc-800 shadow-2xl">
        <h1 className="text-3xl font-bold mb-6 text-center">Join the Waitlist</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">Username</label>
            <input 
              type="text" 
              value={formData.username} 
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-white outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">Email</label>
            <input 
              type="email" 
              value={formData.email} 
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-white outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">Password</label>
            <input 
              type="password" 
              value={formData.password} 
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-white outline-none"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button 
            type="submit" 
            className="w-full py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors"
          >
            Request Beta Access
          </button>
        </form>
        <p className="mt-6 text-center text-zinc-500 text-sm">
          Already have an account? <Link to="/login" className="text-white hover:underline">Sign In</Link>
        </p>
      </div>
    </div>
  );
};

export default SignupPage;
