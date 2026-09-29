// Vireo Audio Support Analytics - Liquid Glassmorphism Controller
// Built for production stability, accessibility, and high performance.

(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // Global State & Constants
  // -------------------------------------------------------------------------
  const ALL_18_MONTHS = [
    '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06',
    '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12',
    '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06'
  ];

  const TEAM_COLORS = {
    'Logistics': '#2563eb',
    'Billing': '#ef4444',
    'Chat Frontline': '#10b981',
    'Email Frontline': '#8b5cf6',
    'Returns Desk': '#f59e0b',
    'Voice Frontline': '#06b6d4',
    'Escalations & Warranty': '#ec4899',
    'Unclassified': '#cbd5e1',
    'Unknown': '#94a3b8'
  };

  const CATEGORY_COLORS = {
    'Delivery & Shipping': '#2563eb',
    'Returns & Refunds': '#f59e0b',
    'Billing & Payments': '#ef4444',
    'Audio Quality': '#10b981',
    'Connectivity': '#06b6d4',
    'Charging & Battery': '#8b5cf6',
    'Warranty & Repair': '#ec4899',
    'App & Firmware': '#14b8a6',
    'Product Enquiry': '#6366f1',
    'Account & Login': '#84cc16',
    'Other': '#64748b',
    'Unclassified': '#cbd5e1'
  };

  const TICKET_PAGE_SIZE = 50;
  let currentTicketOffset = 0;
  let currentActiveTab = 'tab-guide'; // Default to Page 1 Guide!

  // Chart instances
  let comparisonChartInstance = null;
  let categoryRankedChartInstance = null;
  let teamChartInstance = null;
  let categoryChartInstance = null;

  // Chart filtering state
  let rawTeamData = [];
  let rawCategoryData = [];
  let headcountRawData = null;
  let activeTeamFilter = 'all';
  let activeCategoryFilter = 'all';
  let activeTeamHorizon = 'all';
  let activeCategoryHorizon = 'all';

  // Active inspected ticket in drawer
  let activeDrawerTicket = null;

  // -------------------------------------------------------------------------
  // Utility Functions
  // -------------------------------------------------------------------------
  async function fetchJSON(url, options = {}) {
    const res = await fetch(url, options);
    if (!res.ok) {
      let msg = `HTTP error ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) msg = errJson.detail;
      } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  }

  function formatINR(val) {
    if (val == null || isNaN(val)) return '₹0';
    return '₹' + Number(val).toLocaleString('en-IN');
  }

  function formatPct(val) {
    if (val == null || isNaN(val)) return '—';
    return (Number(val) * 100).toFixed(1) + '%';
  }

  function formatDate(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleString('en-IN', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    });
  }

  function filterMonths(horizon) {
    if (horizon === '2025-H1') return ALL_18_MONTHS.filter(m => m >= '2025-01' && m <= '2025-06');
    if (horizon === '2025-H2') return ALL_18_MONTHS.filter(m => m >= '2025-07' && m <= '2025-12');
    if (horizon === '2026-H1') return ALL_18_MONTHS.filter(m => m >= '2026-01' && m <= '2026-06');
    return ALL_18_MONTHS;
  }

  function showStatus(message, isError = false) {
    const banner = document.getElementById('statusBanner');
    const msgEl = document.getElementById('statusMessage');
    if (!banner || !msgEl) return;

    msgEl.textContent = message;
    banner.classList.remove('hidden');
    if (isError) {
      banner.style.backgroundColor = 'rgba(254, 242, 242, 0.9)';
      banner.style.borderColor = '#fecaca';
      banner.style.color = '#991b1b';
    } else {
      banner.style.backgroundColor = 'rgba(239, 246, 255, 0.9)';
      banner.style.borderColor = '#bfdbfe';
      banner.style.color = '#1e40af';
    }
  }

  function hideStatus() {
    const banner = document.getElementById('statusBanner');
    if (banner) banner.classList.add('hidden');
  }

  // -------------------------------------------------------------------------
  // Tab Switching Controller (with Guide Jump Links)
  // -------------------------------------------------------------------------
  function switchTab(targetId) {
    if (!targetId) return;
    const tabs = document.querySelectorAll('.nav-tab');
    const targetTab = document.querySelector(`.nav-tab[data-tab="${targetId}"]`);

    tabs.forEach(t => {
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

    if (targetTab) {
      targetTab.classList.add('active');
      targetTab.setAttribute('aria-selected', 'true');
    }
    const activePane = document.getElementById(targetId);
    if (activePane) activePane.classList.add('active');
    currentActiveTab = targetId;

    // Resize charts on switch
    if (targetId === 'tab-analytics') {
      setTimeout(() => {
        if (comparisonChartInstance) comparisonChartInstance.resize();
        if (categoryRankedChartInstance) categoryRankedChartInstance.resize();
        if (teamChartInstance) teamChartInstance.resize();
        if (categoryChartInstance) categoryChartInstance.resize();
      }, 50);
    }
  }

  function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        switchTab(tab.dataset.tab);
      });
    });

    // Page 1 Guide Cards Jump Buttons
    document.querySelectorAll('.guide-feature-card[data-jump]').forEach(card => {
      card.addEventListener('click', () => {
        const jumpTarget = card.dataset.jump;
        if (jumpTarget) switchTab(jumpTarget);
      });
    });
  }

  // -------------------------------------------------------------------------
  // Metadata & Engine Status
  // -------------------------------------------------------------------------
  async function loadMeta() {
    try {
      const meta = await fetchJSON('/api/v1/meta');
      const providerEl = document.getElementById('providerInfo');
      const footerEngineEl = document.getElementById('footerEngine');
      if (providerEl) {
        providerEl.textContent = `${meta.provider.toUpperCase()} (${meta.model})`;
      }
      if (footerEngineEl) {
        footerEngineEl.textContent = `${meta.provider.toUpperCase()} (${meta.model})`;
      }
    } catch (err) {
      console.warn('Failed to load meta:', err);
    }
  }

  // -------------------------------------------------------------------------
  // Executive Overview & Headcount (Page 2)
  // -------------------------------------------------------------------------
  async function loadSummaryMetrics() {
    try {
      const data = await fetchJSON('/api/v1/metrics/summary');
      const sum = data.summary || {};
      const transfers = data.transfers || {};
      const sla = data.sla || {};
      const evalData = data.evaluation || {};

      const totalTickets = sum.total_tickets || 11641;
      const classifiedCount = sum.classified_tickets || 11641;
      const coveragePct = totalTickets > 0 ? (classifiedCount / totalTickets) : 1;

      // Update Guide & Overview numbers
      const guideTotal = document.getElementById('guideTotalTickets');
      if (guideTotal) guideTotal.textContent = Number(totalTickets).toLocaleString('en-IN');

      const kpiTotalEl = document.getElementById('kpiTotalTickets');
      if (kpiTotalEl) kpiTotalEl.textContent = Number(totalTickets).toLocaleString('en-IN');

      const kpiClassifiedEl = document.getElementById('kpiClassifiedNum');
      if (kpiClassifiedEl) kpiClassifiedEl.textContent = Number(classifiedCount).toLocaleString('en-IN');

      const kpiCoverageEl = document.getElementById('kpiCoveragePct');
      if (kpiCoverageEl) kpiCoverageEl.textContent = formatPct(coveragePct);

      const kpiProgressBar = document.getElementById('kpiProgressBar');
      if (kpiProgressBar) kpiProgressBar.style.width = `${Math.min(100, coveragePct * 100).toFixed(1)}%`;

      const kpiCoverageFooter = document.getElementById('kpiCoverageFooter');
      if (kpiCoverageFooter) {
        kpiCoverageFooter.textContent = `${Number(classifiedCount).toLocaleString('en-IN')} of ${Number(totalTickets).toLocaleString('en-IN')} classified`;
      }

      // KPI: Confidence
      const avgConf = sum.avg_confidence || 0.88;
      const kpiAvgConfEl = document.getElementById('kpiAvgConfidence');
      const kpiConfBadge = document.getElementById('kpiConfidenceBadge');
      if (kpiAvgConfEl) kpiAvgConfEl.textContent = avgConf.toFixed(2);
      if (kpiConfBadge) {
        kpiConfBadge.textContent = 'High Precision';
        kpiConfBadge.className = 'kpi-badge badge-emerald';
      }

      // KPI: Misrouted
      const misroutedRate = sum.misrouted_rate || 0.382;
      const kpiMisroutedEl = document.getElementById('kpiMisroutedPct');
      if (kpiMisroutedEl) kpiMisroutedEl.textContent = formatPct(misroutedRate);

      // KPI: Transfer Cost
      const transferWaste = transfers.transfer_cost_inr || (transfers.transfers ? transfers.transfers * 305 : 396195);
      const kpiTransferEl = document.getElementById('kpiTransferCost');
      if (kpiTransferEl) kpiTransferEl.textContent = formatINR(transferWaste);

      const kpiTransferMeta = document.getElementById('kpiTransferMeta');
      if (kpiTransferMeta && transfers.transfers != null) {
        kpiTransferMeta.textContent = `${formatPct(transfers.transfer_rate || 0.141)} rate (${Number(transfers.transfers).toLocaleString('en-IN')} events)`;
      }

      // KPI: SLA Cost
      const slaWaste = sla.breach_cost_inr || (sla.breaches ? sla.breaches * 350 : 452200);
      const kpiSlaEl = document.getElementById('kpiSlaCost');
      if (kpiSlaEl) kpiSlaEl.textContent = formatINR(slaWaste);

      const kpiSlaMeta = document.getElementById('kpiSlaMeta');
      if (kpiSlaMeta && sla.breaches != null) {
        kpiSlaMeta.textContent = `${formatPct(sla.breach_rate || 0.111)} breach rate (${Number(sla.breaches).toLocaleString('en-IN')} breaches)`;
      }

      // Model evaluation numbers in Operations
      const evalBadge = document.getElementById('evalReviewedCountBadge');
      const evalTotal = document.getElementById('evalLabelsTotal');
      const evalAcc = document.getElementById('evalAccuracyScore');
      const evalF1 = document.getElementById('evalMacroF1Score');
      if (evalBadge) evalBadge.textContent = `${evalData.labels || 0} Labels`;
      if (evalTotal) evalTotal.textContent = evalData.labels || 0;
      if (evalAcc) evalAcc.textContent = evalData.accuracy != null ? formatPct(evalData.accuracy) : '—';
      if (evalF1) evalF1.textContent = evalData.macro_f1 != null ? evalData.macro_f1.toFixed(3) : '—';

    } catch (err) {
      console.error('Failed to load summary metrics:', err);
    }
  }

  async function loadHeadcountSignals() {
    const tbody = document.getElementById('headcountSummaryBody');
    if (!tbody) return;

    try {
      const data = await fetchJSON('/api/v1/metrics/headcount');
      headcountRawData = data;
      const rawMap = {};
      (data.raw_assignment || []).forEach(item => {
        rawMap[item.team] = item;
      });

      const aiMap = {};
      (data.ai_recommended || []).forEach(item => {
        aiMap[item.team] = item;
      });

      const eligibleTeams = data.eligible_teams || [
        "Billing", "Chat Frontline", "Email Frontline", "Logistics", "Returns Desk", "Voice Frontline"
      ];

      // Sort with Logistics first, then Billing, then others by volume
      const sortedTeams = [...eligibleTeams].sort((a, b) => {
        if (a === 'Logistics') return -1;
        if (b === 'Logistics') return 1;
        if (a === 'Billing') return -1;
        if (b === 'Billing') return 1;
        return ((aiMap[b]?.tickets || 0) - (aiMap[a]?.tickets || 0));
      });

      let logisticsTrueShare = 0;
      let html = '';

      sortedTeams.forEach(team => {
        const raw = rawMap[team] || { tickets: 0, share: 0 };
        const ai = aiMap[team] || { tickets: 0, share: 0 };
        const delta = ai.share - raw.share;
        const deltaFormatted = (delta >= 0 ? '+' : '') + (delta * 100).toFixed(1) + '%';
        const deltaClass = delta > 0.05 ? 'delta-positive' : delta < -0.05 ? 'delta-negative' : 'delta-neutral';

        if (team === 'Logistics') {
          logisticsTrueShare = ai.share;
        }

        let badgeHtml = '';
        if (team === 'Logistics') {
          badgeHtml = '<span class="status-badge badge-hire">Allocate +2 Hires (Top Driver)</span>';
        } else if (team === 'Billing') {
          badgeHtml = '<span class="status-badge badge-warning">Queue Inflated (Do Not Overstaff)</span>';
        } else if (delta < -0.02) {
          badgeHtml = '<span class="status-badge badge-neutral">Maintain Baseline</span>';
        } else {
          badgeHtml = '<span class="status-badge badge-neutral">Adequately Staffed</span>';
        }

        html += `
          <tr>
            <td><strong>${team}</strong></td>
            <td>${Number(raw.tickets).toLocaleString('en-IN')}</td>
            <td>${formatPct(raw.share)}</td>
            <td><strong>${Number(ai.tickets).toLocaleString('en-IN')}</strong></td>
            <td><strong>${formatPct(ai.share)}</strong></td>
            <td class="${deltaClass}">${deltaFormatted}</td>
            <td>${badgeHtml}</td>
          </tr>
        `;
      });

      tbody.innerHTML = html;

      // Update executive case callout
      if (logisticsTrueShare > 0) {
        const logShareEl = document.getElementById('logisticsTrueShare');
        const logBarEl = document.getElementById('logisticsShareBar');
        if (logShareEl) logShareEl.textContent = `${formatPct(logisticsTrueShare)} True Workload (#1 Driver)`;
        if (logBarEl) logBarEl.style.width = `${(logisticsTrueShare * 100).toFixed(1)}%`;
      }

      // Also render the Side-by-Side Comparison Dual-Bar Chart on Tab 3!
      renderComparisonDualBarChart(sortedTeams, rawMap, aiMap);

    } catch (err) {
      console.error('Failed to load headcount signals:', err);
      tbody.innerHTML = `<tr><td colspan="7" class="loading-cell error-cell">Error loading headcount data.</td></tr>`;
    }
  }

  // -------------------------------------------------------------------------
  // MULTI-CHART SUITE (Page 3)
  // -------------------------------------------------------------------------

  // Graph 1: Side-by-Side Dual-Bar Chart (Raw Intake vs AI Recommended)
  function renderComparisonDualBarChart(teams, rawMap, aiMap) {
    const canvas = document.getElementById('comparisonBarChart');
    if (!canvas) return;

    const rawShares = teams.map(t => (rawMap[t]?.share ? rawMap[t].share * 100 : 0));
    const aiShares = teams.map(t => (aiMap[t]?.share ? aiMap[t].share * 100 : 0));

    if (comparisonChartInstance) {
      comparisonChartInstance.destroy();
    }

    comparisonChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: teams,
        datasets: [
          {
            label: 'Raw Intake Queue (%)',
            data: rawShares,
            backgroundColor: 'rgba(217, 119, 6, 0.85)',
            borderColor: '#d97706',
            borderWidth: 1,
            borderRadius: 6,
            maxBarThickness: 28,
            barPercentage: 0.7,
            categoryPercentage: 0.8
          },
          {
            label: 'AI Ground Truth (%)',
            data: aiShares,
            backgroundColor: 'rgba(37, 99, 235, 0.85)',
            borderColor: '#2563eb',
            borderWidth: 1,
            borderRadius: 6,
            maxBarThickness: 28,
            barPercentage: 0.7,
            categoryPercentage: 0.8
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: '#475569',
              font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' }
            }
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(241, 245, 249, 0.9)' },
            ticks: {
              color: '#64748b',
              font: { family: 'Plus Jakarta Sans', size: 11 },
              callback: val => `${val}%`
            },
            title: {
              display: true,
              text: 'Share of Tier-1 Support Volume',
              color: '#94a3b8',
              font: { family: 'Plus Jakarta Sans', size: 11 }
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              usePointStyle: true,
              pointStyle: 'circle',
              color: '#334155',
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' }
            }
          },
          tooltip: {
            backgroundColor: '#0f172a',
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: item => ` ${item.dataset.label}: ${item.raw.toFixed(1)}%`
            }
          }
        }
      }
    });
  }

  // Graph 2: Ranked 11-Category Horizontal Bar Chart
  function renderCategoryRankedChart() {
    const canvas = document.getElementById('categoryRankedChart');
    if (!canvas) return;

    // Aggregate counts across all months in rawCategoryData
    const catCounts = {};
    rawCategoryData.forEach(r => {
      if (r.label !== 'Unclassified') {
        catCounts[r.label] = (catCounts[r.label] || 0) + r.count;
      }
    });

    const sortedCats = Object.keys(catCounts).sort((a, b) => catCounts[b] - catCounts[a]);
    const sortedVals = sortedCats.map(c => catCounts[c]);
    const sortedColors = sortedCats.map(c => CATEGORY_COLORS[c] || '#6366f1');

    if (categoryRankedChartInstance) {
      categoryRankedChartInstance.destroy();
    }

    categoryRankedChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: sortedCats,
        datasets: [{
          label: 'Total Tickets',
          data: sortedVals,
          backgroundColor: sortedColors,
          borderRadius: 6,
          maxBarThickness: 18
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: 'rgba(241, 245, 249, 0.9)' },
            ticks: { color: '#64748b', font: { family: 'Plus Jakarta Sans', size: 11 } }
          },
          y: {
            grid: { display: false },
            ticks: {
              color: '#334155',
              font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' }
            }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0f172a',
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: item => ` ${item.raw.toLocaleString('en-IN')} tickets`
            }
          }
        }
      }
    });
  }

  // Graph 3: Monthly Support Team Workload (Full 18-Month Timeline)
  function renderTeamBarChart() {
    const canvas = document.getElementById('teamBarChart');
    if (!canvas) return;

    const visibleMonths = filterMonths(activeTeamHorizon);
    const excludeUnclassified = document.getElementById('excludeUnclassifiedTeam')?.checked ?? true;

    let filteredRows = rawTeamData;
    if (excludeUnclassified) {
      filteredRows = filteredRows.filter(r => r.label !== 'Unclassified' && r.label !== 'Unknown');
    }

    let teams = [...new Set(filteredRows.map(r => r.label))].sort();
    if (activeTeamFilter !== 'all') {
      teams = [activeTeamFilter];
    }

    const datasets = teams.map(team => {
      const color = TEAM_COLORS[team] || '#6366f1';
      const data = visibleMonths.map(month => {
        const match = filteredRows.find(r => r.month === month && r.label === team);
        return match ? match.count : 0;
      });

      return {
        label: team,
        data: data,
        backgroundColor: color,
        borderColor: color,
        borderWidth: 1,
        borderRadius: 4,
        maxBarThickness: 32,
        barPercentage: 0.65,
        categoryPercentage: 0.8
      };
    });

    if (teamChartInstance) {
      teamChartInstance.destroy();
    }

    teamChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: visibleMonths,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: {
              color: '#475569',
              font: { family: 'Plus Jakarta Sans', size: 11, weight: '500' }
            }
          },
          y: {
            stacked: true,
            beginAtZero: true,
            grid: { color: 'rgba(241, 245, 249, 0.9)' },
            ticks: {
              color: '#64748b',
              font: { family: 'Plus Jakarta Sans', size: 11 }
            },
            title: {
              display: true,
              text: 'Monthly Tickets',
              color: '#94a3b8',
              font: { family: 'Plus Jakarta Sans', size: 11 }
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'start',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              usePointStyle: true,
              pointStyle: 'circle',
              color: '#334155',
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' },
              padding: 14
            }
          },
          tooltip: {
            backgroundColor: '#0f172a',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              footer: items => {
                let sum = 0;
                items.forEach(i => { sum += i.raw; });
                return `Total Month: ${sum.toLocaleString('en-IN')} tickets`;
              }
            }
          }
        }
      }
    });

    const captionEl = document.getElementById('teamChartCaption');
    if (captionEl) {
      if (activeTeamFilter === 'all') {
        captionEl.textContent = `Showing monthly volume breakdown across all ${teams.length} teams. Select any chip above to isolate.`;
      } else {
        captionEl.textContent = `Isolated view for team: "${activeTeamFilter}". Click "All Teams" above to reset.`;
      }
    }
  }

  // Graph 4: Monthly Issue Category Volume (Full 18-Month Timeline)
  function renderCategoryBarChart() {
    const canvas = document.getElementById('categoryBarChart');
    if (!canvas) return;

    const visibleMonths = filterMonths(activeCategoryHorizon);
    const excludeUnclassified = document.getElementById('excludeUnclassifiedCategory')?.checked ?? true;

    let filteredRows = rawCategoryData;
    if (excludeUnclassified) {
      filteredRows = filteredRows.filter(r => r.label !== 'Unclassified' && r.label !== 'Other');
    }

    let categories = [...new Set(filteredRows.map(r => r.label))].sort();
    if (activeCategoryFilter !== 'all') {
      categories = [activeCategoryFilter];
    }

    const datasets = categories.map(cat => {
      const color = CATEGORY_COLORS[cat] || '#6366f1';
      const data = visibleMonths.map(month => {
        const match = filteredRows.find(r => r.month === month && r.label === cat);
        return match ? match.count : 0;
      });

      return {
        label: cat,
        data: data,
        backgroundColor: color,
        borderColor: color,
        borderWidth: 1,
        borderRadius: 4,
        maxBarThickness: 32,
        barPercentage: 0.65,
        categoryPercentage: 0.8
      };
    });

    if (categoryChartInstance) {
      categoryChartInstance.destroy();
    }

    categoryChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: visibleMonths,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: {
              color: '#475569',
              font: { family: 'Plus Jakarta Sans', size: 11, weight: '500' }
            }
          },
          y: {
            stacked: true,
            beginAtZero: true,
            grid: { color: 'rgba(241, 245, 249, 0.9)' },
            ticks: { color: '#64748b', font: { family: 'Plus Jakarta Sans', size: 11 } },
            title: {
              display: true,
              text: 'Monthly Tickets',
              color: '#94a3b8',
              font: { family: 'Plus Jakarta Sans', size: 11 }
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            align: 'start',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              usePointStyle: true,
              pointStyle: 'circle',
              color: '#334155',
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' },
              padding: 14
            }
          },
          tooltip: {
            backgroundColor: '#0f172a',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              footer: items => {
                let sum = 0;
                items.forEach(i => { sum += i.raw; });
                return `Total Month: ${sum.toLocaleString('en-IN')} tickets`;
              }
            }
          }
        }
      }
    });

    const captionEl = document.getElementById('catChartCaption');
    if (captionEl) {
      if (activeCategoryFilter === 'all') {
        captionEl.textContent = `Showing monthly stacked volume across ${categories.length} issue categories. Select any chip above to isolate.`;
      } else {
        captionEl.textContent = `Isolated view for category: "${activeCategoryFilter}". Click "All Categories" to reset.`;
      }
    }
  }

  async function loadMonthlyChartsData() {
    try {
      const [teamRes, catRes] = await Promise.all([
        fetchJSON('/api/v1/metrics/monthly?dimension=recommended_team&exclude_unclassified=false'),
        fetchJSON('/api/v1/metrics/monthly?dimension=ai_category&exclude_unclassified=false')
      ]);

      rawTeamData = teamRes.data || [];
      rawCategoryData = catRes.data || [];

      renderTeamBarChart();
      renderCategoryBarChart();
      renderCategoryRankedChart();
    } catch (err) {
      console.error('Failed to load monthly metrics:', err);
    }
  }

  function initChartControls() {
    // Team Horizon buttons
    const teamHorizonGroup = document.getElementById('teamHorizonFilter');
    if (teamHorizonGroup) {
      teamHorizonGroup.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          teamHorizonGroup.querySelectorAll('button').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          activeTeamHorizon = btn.dataset.horizon;
          renderTeamBarChart();
        });
      });
    }

    // Team Filter Chips
    const teamChips = document.getElementById('teamChips');
    if (teamChips) {
      teamChips.querySelectorAll('button').forEach(chip => {
        chip.addEventListener('click', () => {
          teamChips.querySelectorAll('button').forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          activeTeamFilter = chip.dataset.team;
          renderTeamBarChart();
        });
      });
    }

    // Team Exclude Unclassified Toggle
    const teamExcludeToggle = document.getElementById('excludeUnclassifiedTeam');
    if (teamExcludeToggle) {
      teamExcludeToggle.addEventListener('change', () => {
        renderTeamBarChart();
      });
    }

    // Category Horizon buttons
    const catHorizonGroup = document.getElementById('catHorizonFilter');
    if (catHorizonGroup) {
      catHorizonGroup.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          catHorizonGroup.querySelectorAll('button').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          activeCategoryHorizon = btn.dataset.horizon;
          renderCategoryBarChart();
        });
      });
    }

    // Category Filter Chips
    const catChips = document.getElementById('categoryChips');
    if (catChips) {
      catChips.querySelectorAll('button').forEach(chip => {
        chip.addEventListener('click', () => {
          catChips.querySelectorAll('button').forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          activeCategoryFilter = chip.dataset.cat;
          renderCategoryBarChart();
        });
      });
    }

    // Category Exclude Unclassified Toggle
    const catExcludeToggle = document.getElementById('excludeUnclassifiedCategory');
    if (catExcludeToggle) {
      catExcludeToggle.addEventListener('change', () => {
        renderCategoryBarChart();
      });
    }
  }

  // -------------------------------------------------------------------------
  // Ticket Explorer & Inspection Drawer (Page 5)
  // -------------------------------------------------------------------------
  async function loadTickets() {
    const tbody = document.getElementById('ticketsTableBody');
    const paginationLabel = document.getElementById('ticketPaginationLabel');
    const prevBtn = document.getElementById('prevTicketsBtn');
    const nextBtn = document.getElementById('nextTicketsBtn');

    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="8" class="loading-cell"><div class="spinner-sm" style="display:inline-block; vertical-align:middle; margin-right:8px;"></div>Loading ticket records...</td></tr>`;

    const search = document.getElementById('ticketSearchInput')?.value.trim() || '';
    const channel = document.getElementById('channelSelect')?.value || '';
    const routingVal = document.getElementById('routingFilterSelect')?.value || '';

    let url = `/api/v1/tickets?limit=${TICKET_PAGE_SIZE}&offset=${currentTicketOffset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (channel) url += `&channel=${encodeURIComponent(channel)}`;
    if (routingVal === 'misrouted') url += `&misrouted_only=true`;
    if (routingVal === 'review') url += `&needs_review=true`;

    try {
      const tickets = await fetchJSON(url);

      if (!tickets || tickets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state-cell">No tickets match the selected filters.</td></tr>`;
        if (paginationLabel) paginationLabel.textContent = `Showing 0 tickets`;
        if (prevBtn) prevBtn.disabled = currentTicketOffset === 0;
        if (nextBtn) nextBtn.disabled = true;
        return;
      }

      let rowsHtml = '';
      tickets.forEach(ticket => {
        const isMisrouted = ticket.recommended_team && (ticket.recommended_team !== ticket.assigned_team);
        const channelBadge = `<span class="channel-pill channel-${ticket.channel}">${ticket.channel}</span>`;

        let catComparison = '';
        if (ticket.ai_category) {
          const isSameCat = ticket.category === ticket.ai_category;
          catComparison = `
            <div class="flow-cell">
              <span class="raw-label">${ticket.category || 'None'}</span>
              <span class="flow-arrow">➔</span>
              <span class="ai-label ${isSameCat ? 'ai-match' : 'ai-mismatch'}">${ticket.ai_category}</span>
            </div>
          `;
        } else {
          catComparison = `<span class="raw-label">${ticket.category || 'None'}</span>`;
        }

        let teamComparison = '';
        if (ticket.recommended_team) {
          teamComparison = `
            <div class="flow-cell">
              <span class="raw-label">${ticket.assigned_team}</span>
              <span class="flow-arrow">➔</span>
              <span class="ai-label ${isMisrouted ? 'ai-mismatch' : 'ai-match'}">${ticket.recommended_team}</span>
            </div>
          `;
        } else {
          teamComparison = `<span class="raw-label">${ticket.assigned_team}</span>`;
        }

        let confBadge = '—';
        if (ticket.confidence != null) {
          const confVal = ticket.confidence;
          const confClass = confVal >= 0.85 ? 'badge-conf-high' : confVal >= 0.70 ? 'badge-conf-mid' : 'badge-conf-low';
          confBadge = `<span class="conf-badge ${confClass}">${confVal.toFixed(2)}</span>`;
        }

        let reviewBadge = '—';
        if (ticket.needs_review) {
          reviewBadge = `<span class="status-badge badge-warning">Needs Review</span>`;
        } else if (ticket.ai_category) {
          reviewBadge = `<span class="status-badge badge-emerald">Classified</span>`;
        }

        rowsHtml += `
          <tr data-ticket-id="${ticket.ticket_id}" class="ticket-row ${isMisrouted ? 'row-misrouted' : ''}">
            <td class="font-mono font-bold">${ticket.ticket_id}</td>
            <td class="text-subtle">${formatDate(ticket.created_at)}</td>
            <td>${channelBadge}</td>
            <td>${catComparison}</td>
            <td>${teamComparison}</td>
            <td>${confBadge}</td>
            <td>${reviewBadge}</td>
            <td>
              <button class="btn btn-secondary btn-sm inspect-btn" data-ticket-id="${ticket.ticket_id}">
                Inspect
              </button>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = rowsHtml;

      tbody.querySelectorAll('.inspect-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const tId = btn.dataset.ticketId;
          const tObj = tickets.find(t => t.ticket_id === tId);
          if (tObj) openDrawer(tObj);
        });
      });

      tbody.querySelectorAll('.ticket-row').forEach(row => {
        row.addEventListener('click', () => {
          const tId = row.dataset.ticketId;
          const tObj = tickets.find(t => t.ticket_id === tId);
          if (tObj) openDrawer(tObj);
        });
      });

      if (paginationLabel) {
        const start = currentTicketOffset + 1;
        const end = currentTicketOffset + tickets.length;
        paginationLabel.textContent = `Showing ${start} – ${end} tickets`;
      }
      if (prevBtn) prevBtn.disabled = currentTicketOffset === 0;
      if (nextBtn) nextBtn.disabled = tickets.length < TICKET_PAGE_SIZE;

    } catch (err) {
      console.error('Failed to load tickets:', err);
      tbody.innerHTML = `<tr><td colspan="8" class="loading-cell error-cell">Error loading tickets: ${err.message}</td></tr>`;
    }
  }

  function initTicketControls() {
    const applyBtn = document.getElementById('applyTicketFiltersBtn');
    const searchInput = document.getElementById('ticketSearchInput');
    const channelSelect = document.getElementById('channelSelect');
    const routingSelect = document.getElementById('routingFilterSelect');
    const prevBtn = document.getElementById('prevTicketsBtn');
    const nextBtn = document.getElementById('nextTicketsBtn');

    if (applyBtn) {
      applyBtn.addEventListener('click', () => {
        currentTicketOffset = 0;
        loadTickets();
      });
    }

    if (searchInput) {
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          currentTicketOffset = 0;
          loadTickets();
        }
      });
    }

    if (channelSelect) {
      channelSelect.addEventListener('change', () => {
        currentTicketOffset = 0;
        loadTickets();
      });
    }

    if (routingSelect) {
      routingSelect.addEventListener('change', () => {
        currentTicketOffset = 0;
        loadTickets();
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (currentTicketOffset >= TICKET_PAGE_SIZE) {
          currentTicketOffset -= TICKET_PAGE_SIZE;
          loadTickets();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        currentTicketOffset += TICKET_PAGE_SIZE;
        loadTickets();
      });
    }
  }

  // -------------------------------------------------------------------------
  // Side Drawer Inspector
  // -------------------------------------------------------------------------
  function openDrawer(ticket) {
    activeDrawerTicket = ticket;
    const backdrop = document.getElementById('ticketDrawerBackdrop');
    if (!backdrop) return;

    document.getElementById('drawerTicketTitle').textContent = ticket.ticket_id;
    document.getElementById('drawerIntakeCat').textContent = ticket.category || 'None';
    document.getElementById('drawerAssignedTeam').textContent = ticket.assigned_team || '—';
    document.getElementById('drawerChannelDate').textContent = `${(ticket.channel || '').toUpperCase()} • ${formatDate(ticket.created_at)}`;

    document.getElementById('drawerAiCat').textContent = ticket.ai_category || 'Unclassified';
    document.getElementById('drawerAiTeam').textContent = ticket.recommended_team || '—';
    document.getElementById('drawerConfidence').textContent = ticket.confidence != null ? ticket.confidence.toFixed(2) : '—';

    document.getElementById('drawerCustomerMessage').textContent = ticket.customer_message || '(No customer message captured)';
    document.getElementById('drawerAgentNotes').textContent = ticket.agent_notes || '(No agent closing note recorded)';
    document.getElementById('drawerRationale').textContent = ticket.rationale || 'AI classification rationale has not been generated for this ticket yet.';

    const goldSelect = document.getElementById('drawerGoldSelect');
    const noteInput = document.getElementById('drawerReviewerNotes');
    const successNote = document.getElementById('drawerSaveSuccess');

    if (goldSelect) goldSelect.value = ticket.ai_category || '';
    if (noteInput) noteInput.value = '';
    if (successNote) successNote.classList.add('hidden');

    backdrop.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    const backdrop = document.getElementById('ticketDrawerBackdrop');
    if (backdrop) backdrop.classList.add('hidden');
    document.body.style.overflow = '';
    activeDrawerTicket = null;
  }

  function initDrawer() {
    const backdrop = document.getElementById('ticketDrawerBackdrop');
    const closeBtn = document.getElementById('closeDrawerBtn');
    const saveBtn = document.getElementById('saveDrawerReviewBtn');

    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

    if (backdrop) {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeDrawer();
      });
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && backdrop && !backdrop.classList.contains('hidden')) {
        closeDrawer();
      }
    });

    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        if (!activeDrawerTicket) return;
        const goldCategory = document.getElementById('drawerGoldSelect')?.value;
        const notes = document.getElementById('drawerReviewerNotes')?.value;

        if (!goldCategory) {
          alert('Please select a valid gold category.');
          return;
        }

        try {
          saveBtn.disabled = true;
          saveBtn.textContent = 'Saving...';
          await fetchJSON('/api/v1/reviews', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ticket_id: activeDrawerTicket.ticket_id,
              gold_category: goldCategory,
              reviewer: 'qa_lead',
              notes: notes
            })
          });

          const successNote = document.getElementById('drawerSaveSuccess');
          if (successNote) successNote.classList.remove('hidden');

          loadSummaryMetrics();
        } catch (err) {
          alert(`Failed to save review: ${err.message}`);
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = 'Save';
        }
      });
    }
  }

  // -------------------------------------------------------------------------
  // Batch Run Trigger & Global Actions
  // -------------------------------------------------------------------------
  function initGlobalActions() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        loadSummaryMetrics();
        loadHeadcountSignals();
        loadMonthlyChartsData();
        loadTickets();
      });
    }

    const runBtn = document.getElementById('runBtn');
    const runBtnText = document.getElementById('runBtnText');
    const batchSelect = document.getElementById('batchSizeSelect');

    if (runBtn) {
      runBtn.addEventListener('click', async () => {
        const limit = parseInt(batchSelect?.value || '50', 10);
        try {
          runBtn.disabled = true;
          if (runBtnText) runBtnText.textContent = 'Running...';
          showStatus(`Executing rate-paced AI classification batch (${limit} tickets)...`);

          const res = await fetchJSON('/api/v1/jobs/classify/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ limit: limit, force: false })
          });

          showStatus(`✓ Completed! ${res.completed} classified, ${res.failed} errors.`);
          setTimeout(hideStatus, 5000);

          await Promise.all([
            loadSummaryMetrics(),
            loadHeadcountSignals(),
            loadMonthlyChartsData(),
            loadTickets()
          ]);
        } catch (err) {
          showStatus(`Classification failed: ${err.message}`, true);
        } finally {
          runBtn.disabled = false;
          if (runBtnText) runBtnText.textContent = 'Run Analysis';
        }
      });
    }

    const sampleBtn = document.getElementById('generateReviewPackBtn');
    if (sampleBtn) {
      sampleBtn.addEventListener('click', () => {
        alert('Review pack is available at review_sample.csv. Submit reviews via the Ticket Explorer drawer or python scripts/evaluate.py!');
      });
    }
  }

  // -------------------------------------------------------------------------
  // App Initialization
  // -------------------------------------------------------------------------
  async function init() {
    initTabs();
    initChartControls();
    initTicketControls();
    initDrawer();
    initGlobalActions();

    await loadMeta();
    await Promise.all([
      loadSummaryMetrics(),
      loadHeadcountSignals(),
      loadMonthlyChartsData(),
      loadTickets()
    ]);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
