<script setup>
import { ref, computed, onMounted } from "vue";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  PointElement, LineElement,
  Title, Tooltip, Legend
} from "chart.js";
import { Bar, Scatter } from "vue-chartjs";

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend);

// State
const data = ref(null);
const loading = ref(true);
const error = ref(null);
const activeTab = ref("overview");
const detailPage = ref(0);
const filterSignal = ref("all");
const filterOutcome = ref("all");
const PAGE_SIZE = 50;

// Load data
onMounted(async () => {
  try {
    const resp = await fetch("/backtest_results.json");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    data.value = await resp.json();
  } catch (e) {
    // Try loading from absolute path
    try {
      const resp = await fetch(
        "/C:/Users/Administrator/.codex/plugins/cache/personal/xiaochan/0.1.0+codex.20260611121818/logs/backtest_results.json"
      );
      if (resp.ok) data.value = await resp.json();
      else error.value = "找不到 backtest_results.json，请复制到 public/ 目录";
    } catch {
      error.value = "找不到 backtest_results.json。请运行压测后复制到 public/ 目录";
    }
  }
  loading.value = false;
});

// Computed
const overview = computed(() => data.value?.overview || {});
const config = computed(() => data.value?.config || {});
const byType = computed(() => data.value?.by_signal_type || {});
const byConf = computed(() => data.value?.by_confidence || {});
const pnlDist = computed(() => data.value?.pnl_distribution || {});
const allResults = computed(() => data.value?.results || []);

const filteredResults = computed(() => {
  let r = allResults.value.filter(r => r.has_signal && r.outcome !== "no_signal");
  if (filterSignal.value !== "all") r = r.filter(x => x.signal_type === filterSignal.value);
  if (filterOutcome.value !== "all") r = r.filter(x => x.outcome === filterOutcome.value);
  return r;
});

const pagedResults = computed(() => {
  const start = detailPage.value * PAGE_SIZE;
  return filteredResults.value.slice(start, start + PAGE_SIZE);
});

const totalPages = computed(() => Math.ceil(filteredResults.value.length / PAGE_SIZE));

// PnL distribution chart
const pnlChartData = computed(() => {
  const keys = Object.keys(pnlDist.value).map(Number).sort((a, b) => a - b);
  return {
    labels: keys.map(k => k.toFixed(1) + "%"),
    datasets: [{
      label: "交易次数",
      data: keys.map(k => pnlDist.value[k]),
      backgroundColor: keys.map(k => k >= 0 ? "rgba(63,185,80,0.6)" : "rgba(248,81,73,0.6)"),
      borderColor: keys.map(k => k >= 0 ? "#3fb950" : "#f85149"),
      borderWidth: 1,
    }],
  };
});

const pnlChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#8b949e" } } },
  scales: {
    x: { ticks: { color: "#8b949e", maxTicksLimit: 20 }, grid: { color: "#21262d" } },
    y: { ticks: { color: "#8b949e" }, grid: { color: "#21262d" } },
  },
};

// Signal type chart
const typeChartData = computed(() => {
  const entries = Object.entries(byType.value);
  return {
    labels: entries.map(([t]) => t),
    datasets: [
      {
        label: "胜率 %", yAxisID: "y",
        data: entries.map(([, v]) => v.win_rate),
        backgroundColor: "rgba(88,166,255,0.6)", borderColor: "#58a6ff", borderWidth: 1,
      },
      {
        label: "平均 PnL %", yAxisID: "y1",
        data: entries.map(([, v]) => v.avg_pnl),
        backgroundColor: "rgba(210,153,29,0.6)", borderColor: "#d2991d", borderWidth: 1,
      },
    ],
  };
});

const typeChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#8b949e" } } },
  scales: {
    y: { position: "left", ticks: { color: "#58a6ff" }, grid: { color: "#21262d" }, title: { display: true, text: "胜率 %", color: "#58a6ff" } },
    y1: { position: "right", ticks: { color: "#d2991d" }, grid: { drawOnChartArea: false }, title: { display: true, text: "PnL %", color: "#d2991d" } },
    x: { ticks: { color: "#8b949e" } },
  },
};

// Confidence chart
const confChartData = computed(() => {
  const entries = Object.entries(byConf.value);
  return {
    datasets: [{
      label: "胜率 vs 置信度",
      data: entries.map(([k, v]) => ({
        x: parseFloat(k) * 100,
        y: v.win_rate,
        r: Math.max(3, Math.sqrt(v.total) * 2),
      })),
      backgroundColor: entries.map(([, v]) =>
        v.win_rate >= 60 ? "rgba(63,185,80,0.7)" :
        v.win_rate >= 45 ? "rgba(210,153,29,0.7)" : "rgba(248,81,73,0.7)"
      ),
    }],
  };
});

const confChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: "#8b949e" } },
    tooltip: { callbacks: { label: ctx => `胜率: ${ctx.raw.y.toFixed(1)}% | 样本: ${Math.round(ctx.raw.r * ctx.raw.r / 4)}笔` } },
  },
  scales: {
    x: { title: { display: true, text: "信号置信度", color: "#8b949e" }, ticks: { color: "#8b949e", callback: v => v + "%" }, grid: { color: "#21262d" } },
    y: { title: { display: true, text: "实际胜率 %", color: "#8b949e" }, ticks: { color: "#8b949e" }, min: 0, max: 100, grid: { color: "#21262d" } },
  },
};

// Helpers
const signalTypes = computed(() => Object.keys(byType.value));
const wrColor = (v) => v >= 60 ? "#3fb950" : v >= 45 ? "#d2991d" : "#f85149";
const pnlSign = (v) => (v >= 0 ? "+" : "") + v;
const outcomeLabel = (o) => ({ win: "胜", loss: "负", timeout: "超时" }[o] || o);
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>小缠 · 缠论回测看板</h1>
      <p v-if="config.timestamp">{{ config.total_runs }} runs | {{ config.timestamp.substring(0, 19) }}</p>
    </header>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else>
      <!-- Overview Cards -->
      <div class="cards">
        <div class="card">
          <div class="value" :style="{ color: wrColor(overview.win_rate) }">{{ overview.win_rate }}%</div>
          <div class="label">胜率</div>
          <div class="sub">{{ overview.win_count }}W / {{ overview.loss_count }}L</div>
        </div>
        <div class="card">
          <div class="value blue">{{ pnlSign(overview.avg_pnl_pct) }}%</div>
          <div class="label">平均盈亏</div>
        </div>
        <div class="card">
          <div class="value">{{ overview.signal_rate }}%</div>
          <div class="label">信号率</div>
          <div class="sub">{{ overview.signal_count }} / {{ overview.total_runs }}</div>
        </div>
        <div class="card">
          <div class="value">{{ overview.avg_risk_reward.toFixed(1) }}</div>
          <div class="label">平均盈亏比</div>
        </div>
        <div class="card">
          <div class="value">{{ overview.avg_bars_held.toFixed(1) }}</div>
          <div class="label">均持K线</div>
        </div>
        <div class="card">
          <div class="value">{{ overview.speed_runs_per_s.toFixed(0) }}/s</div>
          <div class="label">压测速度</div>
          <div class="sub">{{ overview.total_time_s.toFixed(1) }}s</div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">总览</button>
        <button :class="{ active: activeTab === 'byType' }" @click="activeTab = 'byType'">按信号</button>
        <button :class="{ active: activeTab === 'byConf' }" @click="activeTab = 'byConf'">置信度</button>
        <button :class="{ active: activeTab === 'detail' }" @click="activeTab = 'detail'">明细</button>
      </div>

      <!-- Tab: Overview -->
      <div v-show="activeTab === 'overview'" class="grid2">
        <div class="panel">
          <h3>PnL 分布</h3>
          <div class="chart-wrap"><Bar :data="pnlChartData" :options="pnlChartOptions" /></div>
        </div>
        <div class="panel">
          <h3>胜率 vs 平均盈亏（按信号）</h3>
          <div class="chart-wrap"><Bar :data="typeChartData" :options="typeChartOptions" /></div>
        </div>
      </div>

      <!-- Tab: By Type -->
      <div v-show="activeTab === 'byType'" class="panel">
        <table>
          <thead>
            <tr><th>信号类型</th><th>总次数</th><th>胜</th><th>负</th><th>胜率</th><th>平均 PnL</th></tr>
          </thead>
          <tbody>
            <tr v-for="(v, t) in byType" :key="t">
              <td>{{ t }}</td>
              <td>{{ v.total }}</td>
              <td class="green">{{ v.wins }}</td>
              <td class="red">{{ v.losses }}</td>
              <td :style="{ color: wrColor(v.win_rate) }">{{ v.win_rate }}%</td>
              <td :class="v.avg_pnl >= 0 ? 'green' : 'red'">{{ pnlSign(v.avg_pnl) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Tab: Confidence -->
      <div v-show="activeTab === 'byConf'" class="panel">
        <h3>置信度 → 真实胜率（气泡=样本量）</h3>
        <div class="chart-wrap tall"><Scatter :data="confChartData" :options="confChartOptions" /></div>
      </div>

      <!-- Tab: Detail -->
      <div v-show="activeTab === 'detail'" class="panel">
        <div class="filters">
          <select v-model="filterSignal">
            <option value="all">全部信号</option>
            <option v-for="t in signalTypes" :key="t" :value="t">{{ t }}</option>
          </select>
          <select v-model="filterOutcome">
            <option value="all">全部结果</option>
            <option value="win">胜</option>
            <option value="loss">负</option>
            <option value="timeout">超时</option>
          </select>
          <span class="count">{{ filteredResults.length }} 条</span>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>#</th><th>信号</th><th>方向</th><th>置信度</th><th>入场</th><th>止损</th><th>止盈</th><th>盈亏比</th><th>结果</th><th>PnL%</th><th>持仓K</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in pagedResults" :key="r.run_id">
                <td>{{ r.run_id }}</td>
                <td>{{ r.signal_type }}</td>
                <td>{{ r.recommendation === 'long' ? '多' : '空' }}</td>
                <td>{{ (r.confidence * 100).toFixed(0) }}%</td>
                <td>${{ r.entry_price }}</td>
                <td>${{ r.stop_loss }}</td>
                <td>${{ r.take_profit }}</td>
                <td>{{ r.risk_reward.toFixed(1) }}</td>
                <td :class="r.outcome">{{ outcomeLabel(r.outcome) }}</td>
                <td :class="r.pnl_pct >= 0 ? 'green' : 'red'">{{ pnlSign(r.pnl_pct) }}%</td>
                <td>{{ r.bars_held }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination">
          <button @click="detailPage = Math.max(0, detailPage - 1)" :disabled="detailPage === 0">上一页</button>
          <span>{{ detailPage + 1 }} / {{ totalPages || 1 }}</span>
          <button @click="detailPage = Math.min(totalPages - 1, detailPage + 1)" :disabled="detailPage >= totalPages - 1">下一页</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0f1117; color: #e1e4e8; font-family: 'Segoe UI', system-ui, sans-serif; }
.app { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }
.header { margin-bottom: 20px; }
.header h1 { font-size: 22px; color: #58a6ff; }
.header p { font-size: 13px; color: #8b949e; margin-top: 4px; }

.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; }
.card .value { font-size: 26px; font-weight: 700; }
.card .label { font-size: 12px; color: #8b949e; margin-top: 4px; }
.card .sub { font-size: 11px; color: #6e7681; }

.tabs { display: flex; gap: 2px; margin-bottom: 16px; }
.tabs button { padding: 8px 18px; background: #21262d; border: 1px solid #30363d; border-radius: 6px 6px 0 0; color: #8b949e; cursor: pointer; font-size: 13px; }
.tabs button.active { background: #161b22; color: #58a6ff; border-bottom-color: #161b22; }

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 800px) { .grid2 { grid-template-columns: 1fr; } }

.panel { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.panel h3 { font-size: 14px; color: #c9d1d9; margin-bottom: 12px; }
.chart-wrap { height: 280px; }
.chart-wrap.tall { height: 380px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 10px; background: #21262d; color: #c9d1d9; font-weight: 600; border-bottom: 2px solid #30363d; white-space: nowrap; }
td { padding: 7px 10px; border-bottom: 1px solid #21262d; }
tr:hover td { background: #1c2128; }

.green { color: #3fb950; }
.red { color: #f85149; }
.blue { color: #58a6ff; }
.win { color: #3fb950; font-weight: 600; }
.loss { color: #f85149; font-weight: 600; }
.timeout { color: #8b949e; }

.filters { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.filters select { padding: 6px 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e1e4e8; font-size: 13px; }
.filters .count { font-size: 12px; color: #8b949e; }

.table-scroll { max-height: 420px; overflow: auto; }
.pagination { display: flex; gap: 12px; align-items: center; justify-content: center; padding: 12px 0; font-size: 13px; color: #8b949e; }
.pagination button { padding: 6px 14px; background: #21262d; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; cursor: pointer; font-size: 12px; }
.pagination button:disabled { opacity: 0.4; cursor: default; }

.loading, .error { text-align: center; padding: 60px; color: #8b949e; font-size: 14px; }
.error { color: #f85149; }
</style>
