"use client";
import { motion } from "framer-motion";
import { useStore } from "@/lib/store";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import { BarChart3, Brain, TrendingUp, AlertTriangle, Database, Award } from "lucide-react";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const PLOTLY_LAYOUT_DEFAULTS = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#9ca3af", size: 11 },
  margin: { t: 50, b: 50, l: 50, r: 20 },
  xaxis: { gridcolor: "rgba(99,102,241,0.1)", zerolinecolor: "rgba(99,102,241,0.2)" },
  yaxis: { gridcolor: "rgba(99,102,241,0.1)", zerolinecolor: "rgba(99,102,241,0.2)" },
};

function StatCard({ icon: Icon, label, value, color = "text-brand-500" }: any) {
  return (
    <div className="glass p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

function InsightCard({ title, content }: { title: string; content: string }) {
  return (
    <div className="glass p-5">
      <h3 className="text-sm font-semibold text-brand-500 mb-3">{title}</h3>
      <div className="text-sm text-gray-300 prose prose-invert max-w-none prose-sm">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

export default function ResultsDashboard() {
  const { results, activeTab, setActiveTab } = useStore();
  if (!results) return null;

  const { eda_report, ml_results, forecast_results, anomaly_results, schema_info } = results;
  const numCols = eda_report?.numeric_columns?.length || 0;
  const catCols = eda_report?.categorical_columns?.length || 0;

  const tabs = [
    { id: "overview",  label: "Overview",  icon: Database },
    { id: "eda",       label: "EDA",       icon: BarChart3 },
    { id: "ml",        label: "ML",        icon: Brain },
    { id: "forecast",  label: "Forecast",  icon: TrendingUp },
    { id: "anomaly",   label: "Anomaly",   icon: AlertTriangle },
  ];

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-1 p-1 glass rounded-xl">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 flex-1 justify-center py-2 px-3 rounded-lg text-sm font-medium transition-all
              ${activeTab === tab.id
                ? "bg-brand-500 text-white shadow-lg"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"}`}
          >
            <tab.icon className="w-4 h-4" />
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === "overview" && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard icon={Database} label="Total Rows" value={results.row_count?.toLocaleString() || "—"} />
            <StatCard icon={BarChart3} label="Columns" value={results.column_count || "—"} color="text-purple-400" />
            <StatCard icon={Brain} label="Numeric Cols" value={numCols} color="text-green-400" />
            <StatCard icon={Award} label="Categorical" value={catCols} color="text-yellow-400" />
          </div>
          {schema_info?.llm_summary && (
            <InsightCard title="🤖 AI Dataset Summary" content={schema_info.llm_summary} />
          )}
          {schema_info?.cleaning_steps?.length > 0 && (
            <div className="glass p-5">
              <h3 className="text-sm font-semibold text-brand-500 mb-3">🧹 Data Cleaning Steps</h3>
              <ul className="space-y-1.5">
                {schema_info.cleaning_steps.map((step: string, i: number) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
                    <span className="text-green-400">✓</span> {step}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      )}

      {/* EDA */}
      {activeTab === "eda" && eda_report && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {eda_report.insights && (
            <InsightCard title="🔍 AI-Generated Insights" content={eda_report.insights} />
          )}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {eda_report.charts?.map((chart: any, i: number) => (
              <div key={i} className="glass p-2 rounded-xl overflow-hidden">
                <Plot
                  data={chart.data.data}
                  layout={{ ...chart.data.layout, ...PLOTLY_LAYOUT_DEFAULTS }}
                  config={{ responsive: true, displayModeBar: false }}
                  style={{ width: "100%" }}
                />
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ML */}
      {activeTab === "ml" && ml_results && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {/* Best model banner */}
          <div className="gradient-border p-5">
            <div className="flex items-center gap-3 mb-3">
              <Award className="w-6 h-6 text-yellow-400" />
              <div>
                <p className="text-xs text-gray-400">Best Model</p>
                <p className="text-xl font-bold text-white">{ml_results.best_model}</p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-xs text-gray-400">Task Type</p>
                <span className={`text-sm font-semibold px-3 py-1 rounded-full
                  ${ml_results.task_type === "classification" ? "bg-blue-500/20 text-blue-400" : "bg-green-500/20 text-green-400"}`}>
                  {ml_results.task_type}
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-400">Target: <span className="text-white font-medium">{ml_results.target_column}</span></p>
          </div>

          {/* All models comparison */}
          <div className="glass p-5">
            <h3 className="text-sm font-semibold text-brand-500 mb-4">Model Comparison</h3>
            <div className="space-y-3">
              {Object.entries(ml_results.all_models || {}).map(([name, metrics]: [string, any]) => (
                <div key={name} className={`p-3 rounded-lg border ${name === ml_results.best_model ? "border-brand-500/50 bg-brand-500/5" : "border-gray-700 bg-gray-800/50"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-200">{name}</span>
                    {name === ml_results.best_model && <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full">Best</span>}
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(metrics).map(([k, v]: [string, any]) => (
                      <div key={k} className="text-center">
                        <p className="text-xs text-gray-500 uppercase">{k.replace("_", " ")}</p>
                        <p className="text-sm font-bold text-white">{typeof v === "number" ? v.toFixed(4) : v}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Feature importance */}
          {ml_results.feature_importance_shap && Object.keys(ml_results.feature_importance_shap).length > 0 && (
            <div className="glass p-5">
              <h3 className="text-sm font-semibold text-brand-500 mb-4">🎯 SHAP Feature Importance</h3>
              <div className="space-y-2">
                {Object.entries(ml_results.feature_importance_shap).slice(0, 12).map(([feat, val]: [string, any]) => {
                  const max = Object.values(ml_results.feature_importance_shap)[0] as number;
                  const pct = max > 0 ? (val / max) * 100 : 0;
                  return (
                    <div key={feat} className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-32 truncate flex-shrink-0">{feat}</span>
                      <div className="flex-1 bg-gray-800 rounded-full h-2">
                        <div className="h-2 rounded-full bg-gradient-to-r from-brand-500 to-purple-500"
                          style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-400 w-12 text-right">{val.toFixed(3)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Forecast */}
      {activeTab === "forecast" && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {forecast_results?.skipped ? (
            <div className="glass p-8 text-center text-gray-400">
              <TrendingUp className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>No datetime columns detected — forecasting skipped</p>
            </div>
          ) : forecast_results?.error ? (
            <div className="glass p-5 text-red-400 text-sm">Error: {forecast_results.error}</div>
          ) : forecast_results ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <StatCard icon={TrendingUp} label="Trend" value={forecast_results.trend_direction || "—"} color="text-green-400" />
                <StatCard icon={BarChart3} label="Last Actual" value={forecast_results.last_actual?.toFixed(2) || "—"} color="text-blue-400" />
                <StatCard icon={Award} label="30d Forecast" value={forecast_results.forecast_30d?.toFixed(2) || "—"} color="text-yellow-400" />
              </div>
              {forecast_results.forecast_chart && (
                <div className="glass p-2">
                  <Plot
                    data={forecast_results.forecast_chart.data}
                    layout={{ ...forecast_results.forecast_chart.layout, ...PLOTLY_LAYOUT_DEFAULTS, height: 400 }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: "100%" }}
                  />
                </div>
              )}
              {forecast_results.ai_insights && (
                <InsightCard title="📊 AI Forecast Analysis" content={forecast_results.ai_insights} />
              )}
            </>
          ) : null}
        </motion.div>
      )}

      {/* Anomaly */}
      {activeTab === "anomaly" && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {anomaly_results?.error ? (
            <div className="glass p-5 text-red-400 text-sm">Error: {anomaly_results.error}</div>
          ) : anomaly_results ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <StatCard icon={AlertTriangle} label="Anomalies Found" value={anomaly_results.n_anomalies || 0} color="text-red-400" />
                <StatCard icon={BarChart3} label="Anomaly Rate" value={`${anomaly_results.anomaly_rate_pct || 0}%`} color="text-orange-400" />
                <StatCard icon={Brain} label="Method" value={anomaly_results.method || "—"} color="text-purple-400" />
              </div>
              {anomaly_results.score_distribution_chart && (
                <div className="glass p-2">
                  <Plot
                    data={anomaly_results.score_distribution_chart.data}
                    layout={{ ...anomaly_results.score_distribution_chart.layout, ...PLOTLY_LAYOUT_DEFAULTS, height: 300 }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: "100%" }}
                  />
                </div>
              )}
              {anomaly_results.scatter_chart && (
                <div className="glass p-2">
                  <Plot
                    data={anomaly_results.scatter_chart.data}
                    layout={{ ...anomaly_results.scatter_chart.layout, ...PLOTLY_LAYOUT_DEFAULTS, height: 300 }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: "100%" }}
                  />
                </div>
              )}
              {anomaly_results.ai_report && (
                <InsightCard title="🚨 AI Anomaly Report" content={anomaly_results.ai_report} />
              )}
            </>
          ) : null}
        </motion.div>
      )}
    </div>
  );
}
