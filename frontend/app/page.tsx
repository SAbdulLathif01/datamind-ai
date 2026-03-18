"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "@/lib/store";
import UploadZone from "@/components/UploadZone";
import AgentFeed from "@/components/AgentFeed";
import ChatPanel from "@/components/ChatPanel";
import ResultsDashboard from "@/components/ResultsDashboard";
import { Zap, Github, FileText, Loader2, CheckCircle } from "lucide-react";

export default function Home() {
  const { sessionId, filename, isAnalyzing, analysisComplete, activities } = useStore();
  const hasSession = !!sessionId;

  return (
    <div className="min-h-screen bg-[#030712]">
      {/* Grid background */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* Top nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-gray-800/50 bg-[#030712]/80 backdrop-blur-xl">
        <div className="max-w-screen-2xl mx-auto px-6 h-14 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-brand-500/20 flex items-center justify-center">
              <Zap className="w-4 h-4 text-brand-500" />
            </div>
            <span className="font-bold text-white">DataMind <span className="text-brand-500">AI</span></span>
          </div>

          {hasSession && (
            <div className="flex items-center gap-2 ml-4">
              <FileText className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-400 truncate max-w-[200px]">{filename}</span>
              {isAnalyzing && (
                <span className="flex items-center gap-1 text-xs text-yellow-400">
                  <Loader2 className="w-3 h-3 animate-spin" /> Analyzing
                </span>
              )}
              {analysisComplete && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <CheckCircle className="w-3 h-3" /> Complete
                </span>
              )}
            </div>
          )}

          <div className="ml-auto flex items-center gap-3">
            <a href="https://github.com/SAbdulLathif01/datamind-ai" target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors">
              <Github className="w-4 h-4" />
              <span className="hidden sm:inline">GitHub</span>
            </a>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-xs text-brand-500">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
              GPT-4o Powered
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <div className="pt-14 max-w-screen-2xl mx-auto px-4 sm:px-6">
        <AnimatePresence mode="wait">
          {!hasSession ? (
            /* Upload screen */
            <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="py-20">
              <UploadZone />
            </motion.div>
          ) : (
            /* Dashboard */
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="py-4 grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4 h-[calc(100vh-56px)]">

              {/* Left: Results + Chat stacked */}
              <div className="flex flex-col gap-4 min-h-0 overflow-y-auto">
                {/* Agent progress bar */}
                {isAnalyzing && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    className="glass p-4 flex items-center gap-3">
                    <Loader2 className="w-4 h-4 text-brand-500 animate-spin flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm text-gray-300">
                        {activities.length > 0 ? activities[activities.length - 1].message : "Starting agents..."}
                      </p>
                      <div className="mt-2 h-1 bg-gray-800 rounded-full overflow-hidden">
                        <motion.div className="h-full bg-gradient-to-r from-brand-500 to-purple-500 rounded-full"
                          animate={{ width: ["20%", "80%", "60%", "95%"] }}
                          transition={{ duration: 8, times: [0, 0.3, 0.6, 1], ease: "easeInOut" }} />
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Results Dashboard */}
                {analysisComplete && <ResultsDashboard />}

                {/* Chat Panel (below results on large, full on mobile) */}
                <div className="h-[500px] xl:hidden">
                  <ChatPanel />
                </div>
              </div>

              {/* Right: Agent feed + Chat */}
              <div className="hidden xl:flex flex-col gap-4 h-full min-h-0">
                <div className="h-[280px] flex-shrink-0">
                  <AgentFeed />
                </div>
                <div className="flex-1 min-h-0">
                  <ChatPanel />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
