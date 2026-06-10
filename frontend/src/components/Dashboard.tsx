import React, { useState, useRef, useEffect } from "react";
import { cn } from "../lib/utils";
import { 
  Upload, Zap, LogOut, Loader2, FileVideo, 
  FileText, Settings, BarChart3, RefreshCw, AlertCircle, ArrowRight
} from "lucide-react";
import { GlassPanel } from "./common/GlassPanel";
import api from "../api/api";
import { useAuth } from "../context/AuthContext";

interface Props {
  token: string;
  onLogout: () => void;
}

type JobStatus = "queued" | "running" | "rendering" | "completed" | "failed";

interface JobState {
  job_id: string;
  status: JobStatus;
  error?: string;
  video_path?: string;
}

const MAX_POLL_ATTEMPTS = 200; // ~10 minutes at 3s intervals
const MAX_CLIENT_FILE_SIZE_MB = 20;
const ACCEPTED_FILE_TYPES = ".pdf,.docx,.txt";

/** Resolves a video path to a full URL, handling both absolute and relative paths. */
const resolveVideoUrl = (path: string) =>
  path.startsWith("http") ? path : `/api/${path.replace(/^\//, "")}`;

const Dashboard: React.FC<Props> = ({ onLogout }) => {
  const { user, checkAuth } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState("");
  const [renderVideo, setRenderVideo] = useState(true);
  const [job, setJob] = useState<JobState | null>(null);
  const [stage, setStage] = useState<"idle" | "extracting" | "extracted" | "generating">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [isError, setIsError] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef(0);

  // Check onboarding status
  useEffect(() => {
    if (user && !user.has_seen_onboarding) {
      setShowOnboarding(true);
    }
  }, [user]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, []);

  const handleAcknowledgeOnboarding = async () => {
    try {
      await api.post('/user/mark-onboarded');
      await checkAuth(); // Refresh user context
      setShowOnboarding(false);
    } catch (err) {
      console.error('Failed to mark onboarded', err);
      // Even if it fails, hide the popup for this session
      setShowOnboarding(false);
    }
  };

  const pollJob = (jobId: string) => {
    if (pollRef.current) clearTimeout(pollRef.current);
    pollCountRef.current = 0;

    const executePoll = async () => {
      pollCountRef.current += 1;

      if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
        pollRef.current = null;
        setIsError(true);
        setStatusMsg("Polling timeout — job may still be running. Refresh to check status.");
        setStage("idle");
        return;
      }

      try {
        const res = await api.get(`/user/jobs/${jobId}`);
        const data = res.data;
        setJob(data);
        if (data.status === "completed" || data.status === "failed") {
          pollRef.current = null;
          setStage("idle");
          setIsError(data.status === "failed");
          setStatusMsg(data.status === "completed" ? "Generation successful" : `Engine Error: ${data.error || "Unknown error"}`);
          return;
        }
      } catch (err: any) {
        if (err.response?.status === 401) {
          pollRef.current = null;
          setIsError(true);
          setStatusMsg("Session expired. Please log in again.");
          setStage("idle");
          return;
        }
        pollRef.current = null;
        setIsError(true);
        setStatusMsg(`Network Error: ${err.message || "Unknown error"}`);
        return;
      }
      
      pollRef.current = setTimeout(executePoll, 3000);
    };

    executePoll();
  };

  const handleExtract = async () => {
    if (!file) return;
    
    if (file.size === 0) {
      setIsError(true);
      setStatusMsg("The selected file is empty. Please choose a file with content.");
      return;
    }

    setStage("extracting");
    setIsError(false);
    setStatusMsg("Analyzing document structure...");
    
    const form = new FormData();
    form.append("file", file);
    
    try {
      const res = await api.post("/user/upload", form, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      const data = res.data;
      
      setExtractedText(data.extracted_text || "");
      setStage("extracted");
      setStatusMsg(`Successfully extracted ${data.chunk_count ?? 0} semantic units.`);
    } catch (err: any) {
      setIsError(true);
      setStatusMsg(`Extraction Failed: ${err.response?.data?.detail || err.message || "Unknown error"}`);
      setStage("idle");
    }
  };

  const handleGenerate = async () => {
    if (!extractedText) return;
    setStage("generating");
    setIsError(false);
    setStatusMsg("Composing scenes with LLM...");
    
    try {
      const res = await api.post("/user/generate", { 
        extracted_text: extractedText, 
        render_video: renderVideo 
      });
      const data = res.data;

      setJob(data);
      pollJob(data.job_id);
    } catch (err: any) {
      setIsError(true);
      setStatusMsg(`Orchestration Failed: ${err.response?.data?.detail || err.message || "Unknown error"}`);
      setStage("idle");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    const sizeMb = selected.size / (1024 * 1024);
    if (sizeMb > MAX_CLIENT_FILE_SIZE_MB) {
      setFile(null);
      setExtractedText("");
      setJob(null);
      setStage("idle");
      setIsError(true);
      setStatusMsg(`File too large (${sizeMb.toFixed(1)} MB). Maximum is ${MAX_CLIENT_FILE_SIZE_MB} MB.`);
      return;
    }

    if (selected.size === 0) {
      setFile(null);
      setExtractedText("");
      setJob(null);
      setStage("idle");
      setIsError(true);
      setStatusMsg("The selected file is empty. Please choose a file with content.");
      return;
    }

    setFile(selected);
    setExtractedText("");
    setJob(null);
    setStatusMsg("");
    setIsError(false);
    setStage("idle");
  };


  return (
    <div className="min-h-screen bg-background text-zinc-100 flex flex-col font-sans">
      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 max-w-md w-full shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-purple to-accent-blue" />
            <h2 className="text-2xl font-bold mb-2">Welcome to Beta!</h2>
            <p className="text-zinc-400 mb-6 leading-relaxed">
              You've been granted beta access to Savra Video Generator. To optimize our resources during this phase, usage is currently limited:
            </p>
            <div className="bg-black/50 border border-white/5 rounded-xl p-4 mb-6 flex items-start gap-4">
              <Zap className="text-accent-blue mt-1 shrink-0" size={20} />
              <div>
                <strong className="block text-white mb-1">1 Successful Video per 24 hours</strong>
                <span className="text-sm text-zinc-500">Failed attempts or errors do not count towards your daily limit.</span>
              </div>
            </div>
            <button 
              onClick={handleAcknowledgeOnboarding}
              className="w-full py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors"
            >
              I Understand
            </button>
          </div>
        </div>
      )}

      <nav className="h-16 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 bg-accent-blue/20 rounded-lg flex items-center justify-center border border-accent-blue/30">
            <Zap size={16} className="text-accent-blue" />
          </div>
          <h1 className="text-sm font-bold tracking-tight">Savra Video Generator <span className="text-accent-blue text-[10px] bg-accent-blue/10 px-1.5 py-0.5 rounded ml-2 font-bold uppercase tracking-widest">v1.5 Beta</span></h1>
        </div>
        <div className="flex items-center gap-4">
          {user?.is_admin && (
            <button 
              onClick={() => window.location.href = '/admin'}
              className="flex items-center gap-2 px-3 py-1 bg-accent-blue/10 border border-accent-blue/20 rounded-full text-[10px] uppercase tracking-wider text-accent-blue font-bold hover:bg-accent-blue/20 transition-colors"
            >
              Admin Console
            </button>
          )}
          <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-white/5 rounded-full border border-white/10 text-[10px] uppercase tracking-wider text-zinc-500 font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Active Mode: Local/Docker
          </div>
          <div className="text-xs text-zinc-400 hidden sm:block mr-4 border-r border-white/10 pr-4">
            Logged in as <span className="text-white font-bold">{user?.username}</span>
          </div>
          <button onClick={onLogout} className="flex items-center gap-2 text-xs text-zinc-500 hover:text-white transition-colors">
            <LogOut size={14} />
            Sign Out
          </button>
        </div>
      </nav>

      <main className="flex-1 p-6 md:p-10 max-w-[1600px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-8">
          <GlassPanel className="p-8 space-y-6 bg-surface/30">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent-blue/10 rounded-lg border border-accent-blue/20">
                  <Upload size={18} className="text-accent-blue" />
                </div>
                <h2 className="text-lg font-bold tracking-tight">1. Source</h2>
              </div>

              <label className={cn(
                "flex flex-col items-center justify-center h-48 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-300 group",
                file ? "border-emerald-500/20 bg-emerald-500/5" : "border-white/5 bg-background hover:bg-white/[0.02] hover:border-white/10 shadow-inner"
              )}>
                <div className="flex flex-col items-center gap-3">
                  <Upload size={24} className={cn("transition-transform group-hover:-translate-y-1", file ? "text-emerald-500" : "text-zinc-700")} />
                  <div className="text-center px-4">
                    <p className="text-sm font-medium text-zinc-400 break-all">{file ? file.name : "Choose document"}</p>
                    <p className="text-[10px] text-zinc-700 mt-1 uppercase tracking-widest font-bold">PDF, DOCX, TXT</p>
                  </div>
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept={ACCEPTED_FILE_TYPES}
                  onChange={handleFileChange}
                />
              </label>

              <button
                onClick={handleExtract}
                disabled={!file || stage === "extracting"}
                className={cn(
                  "w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all",
                  !file || stage === "extracting" ? "bg-zinc-900 text-zinc-700 cursor-not-allowed border border-white/5" : "bg-white text-background hover:bg-zinc-100 shadow-premium-sm"
                )}
              >
                {stage === "extracting" ? "Analyzing..." : "Extract Semantics"}
              </button>
            </div>

            <div className="space-y-4 pt-6 border-t border-white/5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent-purple/10 rounded-lg border border-accent-purple/20">
                  <Settings size={18} className="text-accent-purple" />
                </div>
                <h2 className="text-lg font-bold tracking-tight">2. Parameters</h2>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-background/50 rounded-xl border border-white/5 shadow-inner">
                  <div className="flex items-center gap-3">
                    <FileVideo size={14} className="text-zinc-600" />
                    <span className="text-xs font-medium text-zinc-500">Render MP4 Artifact</span>
                  </div>
                  <input 
                    type="checkbox" checked={renderVideo} onChange={(e) => setRenderVideo(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-800 bg-zinc-950 text-accent-purple focus:ring-accent-purple/50"
                  />
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={!extractedText || stage === "generating" || job?.status === "running"}
                className={cn(
                  "w-full py-4 rounded-xl text-xs font-bold uppercase tracking-widest transition-all group",
                  !extractedText || stage === "generating" || job?.status === "running"
                    ? "bg-zinc-900 text-zinc-700 cursor-not-allowed border border-white/5"
                    : "bg-accent-purple text-white hover:bg-accent-purple/90 shadow-glow-purple"
                )}
              >
                <div className="flex items-center justify-center gap-2">
                  {stage === "generating" || job?.status === "running" ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} className="group-hover:animate-pulse" />}
                  Orchestrate Video
                </div>
              </button>
            </div>
          </GlassPanel>
        </div>

        <div className="lg:col-span-8 flex flex-col gap-8">
          <GlassPanel className={cn(
            "p-6 flex items-center justify-between transition-colors duration-500",
            isError ? "border-red-500/20 bg-red-500/[0.02]" : "border-accent-blue/10 bg-accent-blue/[0.02]"
          )}>
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center border transition-all",
                isError ? "bg-red-500/10 border-red-500/20" : 
                job?.status === "running" || job?.status === "rendering" ? "bg-accent-blue/10 border-accent-blue/20 animate-pulse shadow-glow-blue" : "bg-white/5 border-white/10"
              )}>
                {isError ? <AlertCircle size={20} className="text-red-500" /> : 
                 job?.status === "running" || job?.status === "rendering" ? <RefreshCw size={20} className="text-accent-blue animate-spin" /> : 
                 <BarChart3 size={20} className="text-zinc-600" />}
              </div>
              <div className="space-y-0.5">
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Pipeline Observer</p>
                <p className={cn("text-xs font-bold transition-all", isError ? "text-red-400" : "text-white")}>
                  {job?.status === "rendering" ? "Rendering video artifacts..." : 
                   job?.status === "running" ? "Composing scenes with LLM..." :
                   statusMsg || "Standby - Waiting for document ingestion"}
                </p>
              </div>
            </div>
            {job?.status === "running" && (
                <div className="text-[10px] font-mono text-accent-blue/70 animate-pulse">POLLING_ACTIVE_...</div>
            )}
          </GlassPanel>

          <GlassPanel className="flex-1 min-h-[500px] flex flex-col overflow-hidden relative group">
            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.01] to-transparent pointer-events-none" />
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-zinc-950/20">
              <div className="flex items-center gap-3">
                <FileVideo size={16} className="text-zinc-600" />
                <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-400">Whiteboard Preview</h2>
              </div>
              {job?.video_path && (
                <a 
                  href={resolveVideoUrl(job.video_path)}
                  target="_blank" rel="noreferrer"
                  className="text-[10px] font-bold uppercase tracking-widest text-accent-blue hover:text-white transition-colors flex items-center gap-1.5"
                >
                  Download Artifact <ArrowRight size={10} />
                </a>
              )}
            </div>
            
            <div className="flex-1 bg-[#050505] relative flex items-center justify-center">
              {job?.video_path ? (
                <video src={resolveVideoUrl(job.video_path)} controls className="w-full h-full object-contain" />
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-white/[0.02] border border-white/5 flex items-center justify-center border-dashed">
                    <FileVideo size={24} className="text-zinc-800" />
                  </div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-700">Waiting for Render Engine</p>
                </div>
              )}
            </div>
          </GlassPanel>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <GlassPanel className="p-6 space-y-4 bg-surface/20">
              <div className="flex items-center gap-3">
                <FileText size={16} className="text-zinc-700" />
                <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Extracted Semantics</h3>
              </div>
              <div className="h-40 overflow-y-auto text-[11px] font-mono text-zinc-500 leading-relaxed custom-scrollbar whitespace-pre-wrap px-1">
                {extractedText || "// ANALYZE_SOURCE_TO_VIEW_CHUNKS"}
              </div>
            </GlassPanel>
            
            <GlassPanel className="p-6 space-y-4 bg-surface/20 border-white/5">
              <div className="flex items-center gap-3">
                <BarChart3 size={16} className="text-zinc-700" />
                <h3 className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Pipeline Health</h3>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-zinc-700 uppercase">Process ID</span>
                  <span className="text-[10px] font-mono text-zinc-500">{job?.job_id?.slice(0, 16) || "EMPTY_ID"}</span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-white/5">
                  <span className="text-[10px] font-bold text-zinc-700 uppercase">Node Registry</span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[9px] font-bold uppercase">Healthy</span>
                </div>
              </div>
            </GlassPanel>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
