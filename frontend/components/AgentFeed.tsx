"use client";
import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore, AgentActivity } from "@/lib/store";
import { Bot, CheckCircle2, XCircle, Loader2, Activity } from "lucide-react";

const AGENT_COLORS: Record<string, string> = {
  IngestAgent:   "text-blue-400",
  EDAAgent:      "text-purple-400",
  MLAgent:       "text-green-400",
  ForecastAgent: "text-yellow-400",
  AnomalyAgent:  "text-red-400",
  ChatAgent:     "text-cyan-400",
  System:        "text-gray-400",
};

const AGENT_ICONS: Record<string, string> = {
  IngestAgent:   "📥",
  EDAAgent:      "🔍",
  MLAgent:       "🤖",
  ForecastAgent: "📈",
  AnomalyAgent:  "🚨",
  ChatAgent:     "💬",
  System:        "⚡",
};

function StatusIcon({ status }: { status: AgentActivity["status"] }) {
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 text-yellow-400 animate-spin flex-shrink-0" />;
  if (status === "done") return <CheckCircle2 className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />;
  if (status === "error") return <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />;
  return null;
}

export default function AgentFeed() {
  const { activities, isAnalyzing } = useStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activities]);

  return (
    <div className="glass h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-gray-800">
        <Activity className="w-4 h-4 text-brand-500" />
        <span className="text-sm font-semibold text-gray-200">Agent Activity</span>
        {isAnalyzing && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-yellow-400">
            <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-0">
        <AnimatePresence initial={false}>
          {activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-gray-600 text-sm">
              <Bot className="w-8 h-8 mb-2 opacity-30" />
              <span>Agents idle — upload a dataset</span>
            </div>
          ) : (
            activities.map((activity, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-800/50 group"
              >
                <span className="text-base flex-shrink-0 mt-0.5">
                  {AGENT_ICONS[activity.agent] || "•"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-xs font-semibold ${AGENT_COLORS[activity.agent] || "text-gray-400"}`}>
                      {activity.agent}
                    </span>
                    <StatusIcon status={activity.status} />
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed break-words">
                    {activity.message}
                  </p>
                </div>
                <span className="text-[10px] text-gray-600 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {new Date(activity.timestamp).toLocaleTimeString()}
                </span>
              </motion.div>
            ))
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
