import React, { useEffect, useState } from 'react';
import api from '../api/api';
import { useAuth } from '../context/AuthContext';
import { Users, Shield, BarChart3, Plus, Check, X, Loader2 } from 'lucide-react';

interface User {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
  is_beta_authorized: boolean;
  created_at: string;
}

const AdminPanel: React.FC = () => {
  const { logout } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', password: '', email: '' });

  const fetchData = async () => {
    try {
      const [uRes, sRes] = await Promise.all([
        api.get('/admin/users'),
        api.get('/admin/stats')
      ]);
      setUsers(uRes.data);
      setStats(sRes.data);
    } catch (err) {
      console.error('Failed to fetch admin data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/admin/users/create', newUser);
      setShowCreateModal(false);
      setNewUser({ username: '', password: '', email: '' });
      await fetchData();
    } catch (err: any) {
      let msg = 'Failed to create user';
      if (err.response?.status === 422) {
        // Handle Pydantic validation errors
        const detail = err.response.data.detail;
        if (Array.isArray(detail)) {
          msg = detail.map((d: any) => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join('\n');
        } else {
          msg = detail;
        }
      } else {
        msg = err.response?.data?.detail || msg;
      }
      alert(msg);
    }
  };

  const handleToggleAuth = async (userId: number, currentAuth: boolean) => {
    setActionLoading(userId);
    try {
      await api.put(`/admin/users/${userId}/approve`, { authorized: !currentAuth });
      await fetchData();
    } catch (err) {
      alert('Action failed');
    } finally {
      setActionLoading(null);
    }
  };

  const [deleteConfirmUser, setDeleteConfirmUser] = useState<User | null>(null);

  const handleDeleteUser = async () => {
    if (!deleteConfirmUser) return;
    setActionLoading(deleteConfirmUser.id);
    try {
      await api.delete(`/admin/users/${deleteConfirmUser.id}`);
      setDeleteConfirmUser(null);
      await fetchData();
    } catch (err) {
      alert('Delete failed');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-white animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-8">
      {/* Delete Confirmation Modal */}
      {deleteConfirmUser && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 max-w-sm w-full shadow-2xl text-center">
            <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <X size={32} />
            </div>
            <h2 className="text-xl font-bold mb-2">Delete User?</h2>
            <p className="text-zinc-500 text-sm mb-8">
              Are you sure you want to permanently delete <span className="text-white font-bold">{deleteConfirmUser.username}</span>? This action cannot be undone.
            </p>
            <div className="flex gap-4">
              <button 
                onClick={() => setDeleteConfirmUser(null)}
                className="flex-1 py-3 bg-zinc-800 text-white rounded-xl hover:bg-zinc-700 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={handleDeleteUser}
                className="flex-1 py-3 bg-red-600 text-white font-bold rounded-xl hover:bg-red-700 transition-colors text-sm"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <h2 className="text-2xl font-bold mb-6">Manual User Creation</h2>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Username</label>
                <input 
                  type="text" 
                  value={newUser.username} 
                  onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-white outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Email</label>
                <input 
                  type="email" 
                  value={newUser.email} 
                  onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-white outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Password</label>
                <input 
                  type="password" 
                  value={newUser.password} 
                  onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl focus:ring-2 focus:ring-white outline-none"
                  required
                />
              </div>
              <div className="flex gap-4 mt-8">
                <button 
                  type="button" 
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 bg-zinc-800 text-white rounded-xl hover:bg-zinc-700 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="flex-1 py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-12">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Admin Console</h1>
            <p className="text-zinc-500 mt-2">Manage beta access and monitor system health.</p>
          </div>
          <div className="flex gap-4">
            <button 
              onClick={() => window.location.href = '/dashboard'}
              className="px-6 py-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 transition-colors text-zinc-400 hover:text-white"
            >
              Switch to User View
            </button>
            <button onClick={logout} className="px-6 py-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 transition-colors">
              Logout
            </button>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-2xl">
            <div className="flex items-center gap-4 mb-2 text-zinc-400">
              <Users size={20} />
              <span className="text-sm font-medium uppercase tracking-wider">Total Users</span>
            </div>
            <div className="text-3xl font-bold">{stats?.total_users || 0}</div>
          </div>
          <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-2xl">
            <div className="flex items-center gap-4 mb-2 text-zinc-400">
              <Check size={20} className="text-green-500" />
              <span className="text-sm font-medium uppercase tracking-wider">Beta Authorized</span>
            </div>
            <div className="text-3xl font-bold">{stats?.beta_users || 0}</div>
          </div>
          <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-2xl">
            <div className="flex items-center gap-4 mb-2 text-zinc-400">
              <BarChart3 size={20} className="text-blue-500" />
              <span className="text-sm font-medium uppercase tracking-wider">Jobs (24h)</span>
            </div>
            <div className="text-3xl font-bold">{stats?.completed_jobs || 0} / {stats?.total_jobs || 0}</div>
          </div>
        </div>

        {/* User Table */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">
          <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
            <h2 className="text-xl font-bold">Access Requests</h2>
            <button 
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-white text-black rounded-lg font-bold text-sm hover:bg-zinc-200"
            >
              <Plus size={16} /> Create User
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-zinc-500 text-sm border-b border-zinc-800">
                  <th className="px-6 py-4 font-medium">User</th>
                  <th className="px-6 py-4 font-medium">Role</th>
                  <th className="px-6 py-4 font-medium">Access</th>
                  <th className="px-6 py-4 font-medium">Registered</th>
                  <th className="px-6 py-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-zinc-800/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium">{u.username}</div>
                      <div className="text-xs text-zinc-500">{u.email}</div>
                    </td>
                    <td className="px-6 py-4">
                      {u.is_admin ? (
                        <span className="flex items-center gap-1 text-xs font-bold text-purple-400">
                          <Shield size={12} /> ADMIN
                        </span>
                      ) : (
                        <span className="text-xs text-zinc-500">USER</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {u.is_beta_authorized ? (
                        <span className="px-2 py-1 bg-green-500/10 text-green-500 text-[10px] font-bold rounded uppercase">Authorized</span>
                      ) : (
                        <span className="px-2 py-1 bg-zinc-800 text-zinc-500 text-[10px] font-bold rounded uppercase">Waitlist</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-zinc-500">
                      {u.created_at === "Unknown" ? "Unknown" : new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        {!(u.is_admin) && (
                          <button 
                            onClick={() => handleToggleAuth(u.id, u.is_beta_authorized)}
                            disabled={actionLoading === u.id}
                            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                              u.is_beta_authorized 
                              ? 'bg-zinc-800 text-red-400 hover:bg-red-500 hover:text-white' 
                              : 'bg-white text-black hover:bg-zinc-200'
                            }`}
                          >
                            {actionLoading === u.id ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : (u.is_beta_authorized ? 'Revoke' : 'Approve')}
                          </button>
                        )}
                        {!(u.is_admin) && (
                          <button 
                            onClick={() => setDeleteConfirmUser(u)}
                            disabled={actionLoading === u.id}
                            className="p-2 bg-zinc-800 text-zinc-500 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all"
                            title="Delete User"
                          >
                            <X size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
