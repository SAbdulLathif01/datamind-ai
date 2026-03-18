"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { useStore } from "@/lib/store";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function UploadZone() {
  const [uploading, setUploading] = useState(false);
  const { setSession, setAnalyzing, connectWS } = useStore();

  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    const file = files[0];
    setUploading(true);

    try {
      // 1. Upload file
      const form = new FormData();
      form.append("file", file);
      const uploadRes = await fetch(`${API}/api/upload`, { method: "POST", body: form });
      if (!uploadRes.ok) throw new Error("Upload failed");
      const { session_id } = await uploadRes.json();

      setSession(session_id, file.name);
      connectWS(session_id);
      setAnalyzing(true);

      // 2. Trigger analysis
      const analyzeRes = await fetch(`${API}/api/analyze/${session_id}`, { method: "POST" });
      if (!analyzeRes.ok) throw new Error("Analysis failed to start");

      toast.success(`Analyzing ${file.name}...`, { description: "Multi-agent pipeline running" });
    } catch (err: any) {
      toast.error("Error", { description: err.message });
      setAnalyzing(false);
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"], "application/json": [".json"] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[60vh] gap-8"
    >
      {/* Hero text */}
      <div className="text-center space-y-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="flex items-center justify-center gap-3 mb-6"
        >
          <div className="w-12 h-12 rounded-xl bg-brand-500/20 flex items-center justify-center glow-accent">
            <Zap className="w-6 h-6 text-brand-500" />
          </div>
          <h1 className="text-5xl font-bold text-glow">
            <span className="text-brand-500">Data</span>Mind AI
          </h1>
        </motion.div>
        <p className="text-xl text-gray-400 max-w-xl">
          Drop any dataset. Seven AI agents analyze it autonomously —
          EDA, ML, forecasting, anomaly detection, and natural language Q&A.
        </p>
      </div>

      {/* Drop zone */}
      <motion.div
        {...getRootProps()}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`
          relative w-full max-w-2xl p-12 rounded-2xl border-2 border-dashed cursor-pointer
          transition-all duration-300 text-center
          ${isDragActive
            ? "border-brand-500 bg-brand-500/10 glow-accent"
            : "border-gray-700 bg-gray-900/50 hover:border-brand-500/50 hover:bg-brand-500/5"
          }
          ${uploading ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input {...getInputProps()} />

        <AnimatePresence mode="wait">
          {uploading ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
              <Loader2 className="w-12 h-12 text-brand-500 animate-spin mx-auto" />
              <p className="text-gray-400">Uploading & starting analysis...</p>
            </motion.div>
          ) : isDragActive ? (
            <motion.div key="drag" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
              <Upload className="w-12 h-12 text-brand-500 mx-auto animate-bounce" />
              <p className="text-brand-500 font-semibold text-lg">Drop it here!</p>
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
              <div className="relative mx-auto w-16 h-16">
                <div className="absolute inset-0 rounded-full bg-brand-500/20 animate-ping" />
                <div className="relative flex items-center justify-center w-16 h-16 rounded-full bg-brand-500/10">
                  <Upload className="w-8 h-8 text-brand-500" />
                </div>
              </div>
              <div>
                <p className="text-white font-semibold text-lg">Drag & drop your dataset</p>
                <p className="text-gray-500 mt-1">or click to browse — CSV, Excel, JSON</p>
              </div>
              <div className="flex items-center justify-center gap-4 mt-4">
                {["CSV", "XLSX", "JSON"].map((fmt) => (
                  <span key={fmt} className="px-3 py-1 rounded-full bg-gray-800 text-gray-400 text-sm border border-gray-700">
                    {fmt}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Feature pills */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex flex-wrap justify-center gap-3"
      >
        {[
          "🔍 Auto EDA", "🤖 ML AutoSelect", "📈 Forecasting",
          "🚨 Anomaly Detection", "💬 NL→SQL Chat", "📊 SHAP Explainability"
        ].map((feat) => (
          <span key={feat} className="px-4 py-2 glass text-sm text-gray-300 rounded-full">
            {feat}
          </span>
        ))}
      </motion.div>
    </motion.div>
  );
}
