import { create } from "zustand";

export interface AgentActivity {
  agent: string;
  message: string;
  timestamp: string;
  status: "running" | "done" | "error";
}

export interface AnalysisResults {
  schema_info?: any;
  eda_report?: any;
  ml_results?: any;
  forecast_results?: any;
  anomaly_results?: any;
  row_count?: number;
  column_count?: number;
  activity_log?: AgentActivity[];
}

interface AppState {
  sessionId: string | null;
  filename: string | null;
  isAnalyzing: boolean;
  analysisComplete: boolean;
  activities: AgentActivity[];
  results: AnalysisResults | null;
  activeTab: string;
  ws: WebSocket | null;

  setSession: (id: string, filename: string) => void;
  setAnalyzing: (v: boolean) => void;
  setComplete: (results: AnalysisResults) => void;
  addActivity: (a: AgentActivity) => void;
  setActiveTab: (tab: string) => void;
  connectWS: (sessionId: string) => void;
  disconnectWS: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API.replace("http", "ws");

export const useStore = create<AppState>((set, get) => ({
  sessionId: null,
  filename: null,
  isAnalyzing: false,
  analysisComplete: false,
  activities: [],
  results: null,
  activeTab: "overview",
  ws: null,

  setSession: (id, filename) => set({ sessionId: id, filename, analysisComplete: false, activities: [], results: null }),
  setAnalyzing: (v) => set({ isAnalyzing: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),

  setComplete: (results) =>
    set({ analysisComplete: true, isAnalyzing: false, results }),

  addActivity: (a) =>
    set((s) => ({ activities: [...s.activities, a] })),

  connectWS: (sessionId) => {
    const existing = get().ws;
    if (existing) existing.close();

    const ws = new WebSocket(`${WS_URL}/ws/${sessionId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "agent_activity") {
        get().addActivity(data.data);
      } else if (data.type === "analysis_complete") {
        get().setComplete(data.data);
      } else if (data.type === "status") {
        get().addActivity({
          agent: "System",
          message: data.message,
          timestamp: new Date().toISOString(),
          status: "running",
        });
      }
    };

    ws.onerror = () => console.error("WebSocket error");
    set({ ws });
  },

  disconnectWS: () => {
    get().ws?.close();
    set({ ws: null });
  },
}));
