import { motion } from "framer-motion";
import { SpotlightCard } from "./common/SpotlightCard";
import React from "react";
import { BackgroundBeams } from "./ui/background-beams";
import { FileText, Zap, Film, ArrowRight } from "lucide-react";
import { IconBrandGithub } from "@tabler/icons-react";

interface Props {
  onGetStarted: () => void;
}

const LandingPage: React.FC<Props> = ({ onGetStarted }) => {
  return (
    <div className="min-h-screen bg-background overflow-x-hidden selection:bg-accent-blue/30">
      {/* ── Hero Section ──────────────────────────── */}
      <section className="relative px-6 pt-32 pb-24 md:pt-48 md:pb-32">
        <BackgroundBeams className="opacity-40" />
        
        <div className="relative z-10 max-w-5xl mx-auto text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <span className="inline-flex items-center gap-2 px-3 py-1 text-xs font-medium text-accent-blue bg-accent-blue/10 border border-accent-blue/20 rounded-full mb-6">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-blue opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-blue"></span>
              </span>
              Now in Beta v1.5
            </span>
            
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-white leading-[1.1]">
              Documents become <br className="hidden md:block" />
              <span className="bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent">
                Whiteboard Stories.
              </span>
            </h1>
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="max-w-2xl mx-auto text-lg md:text-xl text-zinc-400 leading-relaxed"
          >
            Savra Video Generator transforms your static documents into professional, hand-drawn 
            whiteboard animations autonomously. Powered by Gemini and Remotion.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4"
          >
            <button
              onClick={onGetStarted}
              className="group relative flex items-center gap-2 px-8 py-4 bg-white text-zinc-950 font-bold rounded-xl shadow-premium-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              Launch Control Room
              <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </button>
            
            <a
              href="https://github.com/AVPthegreat/savra-video-generator"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-8 py-4 bg-zinc-900 text-zinc-100 font-semibold rounded-xl border border-white/5 hover:bg-zinc-800 transition-all font-sans"
            >
              <IconBrandGithub size={20} />
              Star on GitHub
            </a>
          </motion.div>
        </div>
      </section>

      {/* ── Features Section ──────────────────────── */}
      <section className="px-6 py-24 md:py-32">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SpotlightCard glowColor="rgba(59, 130, 246, 0.1)">
              <div className="w-12 h-12 bg-accent-blue/10 rounded-xl flex items-center justify-center mb-6 border border-accent-blue/20">
                <FileText className="text-accent-blue" size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Semantic Analysis</h3>
              <p className="text-zinc-500 leading-relaxed text-sm">
                Advanced document extraction that understands technical context and hierarchical structures 
                from PDFs and layouts.
              </p>
            </SpotlightCard>

            <SpotlightCard glowColor="rgba(139, 92, 246, 0.1)">
              <div className="w-12 h-12 bg-accent-purple/10 rounded-xl flex items-center justify-center mb-6 border border-accent-purple/20">
                <Zap className="text-accent-purple" size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">LLM Orchestration</h3>
              <p className="text-zinc-500 leading-relaxed text-sm">
                Gemini Multi-modal agents transform text chunks into pedagogical storyboards with 
                choreographed SVG animations.
              </p>
            </SpotlightCard>

            <SpotlightCard glowColor="rgba(255, 255, 255, 0.05)">
              <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center mb-6 border border-white/10">
                <Film className="text-white" size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Frame-Perfect Render</h3>
              <p className="text-zinc-500 leading-relaxed text-sm">
                Distributed rendering pipeline with Remotion produces broadcast-quality MP4 artifacts 
                synced to neural audio.
              </p>
            </SpotlightCard>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────── */}
      <footer className="px-6 py-12 border-t border-white/5 bg-zinc-950/50 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-zinc-500 text-sm font-medium">
          <p>© {new Date().getFullYear()} Savra Video Generator · Anant Vardhan Pandey</p>
          <div className="flex items-center gap-8">
            <a href="https://github.com/AVPthegreat/savra-video-generator" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
