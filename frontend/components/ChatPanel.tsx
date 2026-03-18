"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Loader2, Code2, Table } from "lucide-react";
import { useStore } from "@/lib/store";
import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  table?: any[];
  chart?: any;
  row_count?: number;
}

export default function ChatPanel() {
  const { sessionId, analysisComplete } = useStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "👋 Hi! I'm your data analyst. Ask me anything about your dataset in plain English — I'll translate it to SQL and give you insights.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSql, setShowSql] = useState<Record<number, boolean>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading || !sessionId) return;
    const question = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question }),
      });
      const data = await res.json();
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.answer || data.error || "No response",
          sql: data.sql,
          table: data.table,
          chart: data.chart,
          row_count: data.row_count,
        },
      ]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: "❌ Connection error. Is the backend running?" }]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    "Show me the top 10 rows",
    "What's the average of each numeric column?",
    "Which category has the highest count?",
    "Show trends over time",
    "Find rows where values are unusually high",
  ];

  return (
    <div className="glass h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-gray-800">
        <Bot className="w-4 h-4 text-brand-500" />
        <span className="text-sm font-semibold">Data Chat</span>
        <span className="ml-auto text-xs text-gray-500">NL → SQL → Insights</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              {/* Avatar */}
              <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs
                ${msg.role === "user" ? "bg-brand-500" : "bg-gray-700"}`}>
                {msg.role === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>

              {/* Bubble */}
              <div className={`max-w-[85%] space-y-2 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
                  ${msg.role === "user"
                    ? "bg-brand-500 text-white rounded-tr-sm"
                    : "bg-gray-800 text-gray-200 rounded-tl-sm"}`}>
                  {msg.content}
                </div>

                {/* SQL toggle */}
                {msg.sql && (
                  <button
                    onClick={() => setShowSql((s) => ({ ...s, [i]: !s[i] }))}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand-500 transition-colors"
                  >
                    <Code2 className="w-3 h-3" />
                    {showSql[i] ? "Hide SQL" : "View SQL"}
                  </button>
                )}
                {showSql[i] && msg.sql && (
                  <pre className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs text-green-400 font-mono overflow-x-auto max-w-full">
                    {msg.sql}
                  </pre>
                )}

                {/* Table preview */}
                {msg.table && msg.table.length > 0 && (
                  <div className="w-full overflow-x-auto rounded-lg border border-gray-700">
                    <table className="text-xs text-gray-300 w-full">
                      <thead className="bg-gray-800">
                        <tr>{Object.keys(msg.table[0]).map((k) => (
                          <th key={k} className="px-3 py-2 text-left text-gray-400 font-medium">{k}</th>
                        ))}</tr>
                      </thead>
                      <tbody>
                        {msg.table.slice(0, 8).map((row, ri) => (
                          <tr key={ri} className="border-t border-gray-800 hover:bg-gray-800/50">
                            {Object.values(row).map((v: any, ci) => (
                              <td key={ci} className="px-3 py-2 truncate max-w-[120px]">{String(v)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {msg.row_count && msg.row_count > 8 && (
                      <div className="text-xs text-gray-500 px-3 py-2 bg-gray-800/50">
                        + {msg.row_count - 8} more rows
                      </div>
                    )}
                  </div>
                )}

                {/* Chart */}
                {msg.chart && (
                  <div className="w-full rounded-lg overflow-hidden border border-gray-700">
                    <Plot
                      data={msg.chart.data}
                      layout={{ ...msg.chart.layout, paper_bgcolor: "transparent", plot_bgcolor: "transparent", height: 280, margin: { t: 40, b: 40, l: 40, r: 20 } }}
                      config={{ responsive: true, displayModeBar: false }}
                      style={{ width: "100%" }}
                    />
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {loading && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
                <span className="text-sm text-gray-400">Thinking...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {!analysisComplete && (
        <div className="px-4 py-2 flex gap-2 overflow-x-auto border-t border-gray-800">
          {suggestions.map((s) => (
            <button key={s} onClick={() => setInput(s)}
              className="flex-shrink-0 text-xs px-3 py-1.5 rounded-full bg-gray-800 text-gray-400 hover:bg-brand-500/20 hover:text-brand-500 transition-colors border border-gray-700">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className={`flex gap-2 rounded-xl border transition-colors p-2
          ${!analysisComplete ? "border-gray-700 opacity-50" : "border-gray-600 focus-within:border-brand-500/50"}`}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder={analysisComplete ? "Ask anything about your data..." : "Run analysis first..."}
            disabled={!analysisComplete || loading}
            className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 outline-none px-2"
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading || !analysisComplete}
            className="p-2 rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
