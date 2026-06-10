import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../lib/utils";
import { BackgroundBeams } from "./ui/background-beams";
import { Shield, Lock, User, Terminal, Loader2, ArrowLeft } from "lucide-react";
import { GlassPanel } from "./common/GlassPanel";

interface Props {
  onLogin: (token: string) => void;
  onBack: () => void;
}

const AdminLogin: React.FC<Props> = ({ onLogin, onBack }) => {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isShaking, setIsShaking] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const triggerShake = () => {
    setIsShaking(true);
    setTimeout(() => setIsShaking(false), 500);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({ detail: "Authentication failed" }));
        throw new Error(data.detail || "Authentication failed");
      }

      const data = await resp.json();
      onLogin(data.access_token);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
      triggerShake();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-background flex items-center justify-center p-4 overflow-hidden selection:bg-accent-blue/30">
      <BackgroundBeams className="opacity-40" />

      <motion.div
        initial={{ opacity: 0, scale: 0.98, y: 10 }}
        animate={{ 
          opacity: 1, 
          scale: 1, 
          y: 0,
          x: isShaking ? [0, -8, 8, -8, 8, 0] : 0
        }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-sm"
      >
        <div className="text-center mb-10 space-y-2">
          <div className="inline-flex p-3 bg-white/[0.03] rounded-2xl border border-white/5 mb-4 shadow-premium-sm">
            <Terminal className="text-accent-blue" size={24} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">System Access</h1>
          <p className="text-xs font-bold text-zinc-600 uppercase tracking-[0.2em]">Savra Video Generator Control Room</p>
        </div>

        <GlassPanel className="p-8 shadow-premium-lg border-white/10">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest pl-1">Identifier</label>
              <div className="relative group">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-700 group-focus-within:text-accent-blue transition-colors" size={16} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 bg-background border border-white/5 rounded-xl text-zinc-100 text-sm focus:outline-none focus:border-white/10 focus:bg-white/[0.02] transition-all"
                  placeholder="admin"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest pl-1">Security Key</label>
              <div className="relative group">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-700 group-focus-within:text-accent-blue transition-colors" size={16} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 bg-background border border-white/5 rounded-xl text-zinc-100 text-sm focus:outline-none focus:border-white/10 focus:bg-white/[0.02] transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 bg-red-500/5 border border-red-500/10 rounded-lg flex items-center gap-2 text-red-500 text-[10px] font-bold tracking-wider uppercase"
                >
                  <Shield size={14} />
                  <span>Access Denied: {error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            <button
              type="submit"
              disabled={loading}
              className={cn(
                "w-full py-4 rounded-xl text-xs font-bold tracking-widest uppercase transition-all",
                loading
                  ? "bg-zinc-900 text-zinc-700 cursor-not-allowed"
                  : "bg-white text-background hover:bg-zinc-200 shadow-premium-sm"
              )}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 size={14} className="animate-spin" />
                  Authorizing
                </span>
              ) : (
                "Initiate Entry"
              )}
            </button>
          </form>
        </GlassPanel>

        <button
          onClick={onBack}
          className="mt-8 flex items-center justify-center gap-2 w-full text-zinc-600 hover:text-white text-[10px] font-bold tracking-widest transition-colors uppercase"
        >
          <ArrowLeft size={12} />
          Back to Interface
        </button>
      </motion.div>
    </div>
  );
};

export default AdminLogin;
