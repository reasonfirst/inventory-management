<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="monthlyData.length === 0" class="card empty-state">{{ t('reports.noData') }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('reports.summary.totalRevenue') }}</div>
          <div class="stat-value">{{ money(totalRevenue) }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('reports.summary.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ money(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('reports.summary.totalOrders') }}</div>
          <div class="stat-value">{{ totalOrders.toLocaleString() }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('reports.summary.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter ? formatQuarter(bestQuarter) : '-' }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterly.title') }}</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('reports.quarterly.quarter') }}</th>
                <th class="num">{{ t('reports.quarterly.totalOrders') }}</th>
                <th class="num">{{ t('reports.quarterly.totalRevenue') }}</th>
                <th class="num">{{ t('reports.quarterly.avgOrderValue') }}</th>
                <th class="num">{{ t('reports.quarterly.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ formatQuarter(q.quarter) }}</strong></td>
                <td class="num">{{ q.total_orders }}</td>
                <td class="num">{{ money(q.total_revenue) }}</td>
                <td class="num">{{ money(q.avg_order_value) }}</td>
                <td class="num">
                  <span :class="['badge', getFulfillmentClass(q.fulfillment_rate)]">{{ q.fulfillment_rate }}%</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.trend.title') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="row in monthlyRows" :key="row.month" class="bar-wrapper">
              <div class="bar-container">
                <div class="bar" :style="{ height: row.barHeight + 'px' }" :title="money(row.revenue)"></div>
              </div>
              <div class="bar-label">{{ row.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthly.title') }}</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('reports.monthly.month') }}</th>
                <th class="num">{{ t('reports.monthly.orders') }}</th>
                <th class="num">{{ t('reports.monthly.revenue') }}</th>
                <th class="num">{{ t('reports.monthly.change') }}</th>
                <th class="num">{{ t('reports.monthly.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in monthlyRows" :key="row.month">
                <td><strong>{{ row.label }}</strong></td>
                <td class="num">{{ row.order_count }}</td>
                <td class="num">{{ money(row.revenue) }}</td>
                <td class="num">
                  <span v-if="row.change !== null" :class="changeClass(row.change)">{{ formatChange(row.change) }}</span>
                  <span v-else>-</span>
                </td>
                <td class="num">
                  <span v-if="row.growthRate !== null" :class="changeClass(row.change)">{{ formatGrowth(row.growthRate) }}</span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

const MAX_BAR_HEIGHT = 200
const MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

export default {
  name: 'Reports',
  setup() {
    const { t, currentCurrency } = useI18n()
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        quarterlyData.value = quarterly
        monthlyData.value = monthly
      } catch (err) {
        error.value = t('reports.loadFailed', { message: err.message })
      } finally {
        loading.value = false
      }
    }

    const money = (amount) => formatCurrency(amount, currentCurrency.value)

    // Month keys arrive as YYYY-MM; validate before building a label
    const formatMonth = (monthStr) => {
      const [year, month] = (monthStr || '').split('-')
      const key = MONTH_KEYS[parseInt(month, 10) - 1]
      if (!year || !key) return monthStr
      return t('reports.monthLabel', { month: t(`months.${key}`), year })
    }

    // Quarter keys arrive as Q1-2025
    const formatQuarter = (quarterStr) => {
      const match = /^Q(\d)-(\d{4})$/.exec(quarterStr || '')
      if (!match) return quarterStr
      return t('reports.quarterLabel', { quarter: match[1], year: match[2] })
    }

    const totalRevenue = computed(() => monthlyData.value.reduce((sum, m) => sum + m.revenue, 0))
    const totalOrders = computed(() => monthlyData.value.reduce((sum, m) => sum + m.order_count, 0))
    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length ? totalRevenue.value / monthlyData.value.length : 0
    )
    const bestQuarter = computed(() => {
      const best = quarterlyData.value.reduce(
        (top, q) => (!top || q.total_revenue > top.total_revenue ? q : top),
        null
      )
      return best ? best.quarter : ''
    })

    // Derive chart and table values once per data change instead of per render
    const monthlyRows = computed(() => {
      const maxRevenue = Math.max(0, ...monthlyData.value.map(m => m.revenue))
      return monthlyData.value.map((m, index) => {
        const previous = index > 0 ? monthlyData.value[index - 1].revenue : null
        const change = previous === null ? null : m.revenue - previous
        return {
          ...m,
          label: formatMonth(m.month),
          barHeight: maxRevenue > 0 ? (m.revenue / maxRevenue) * MAX_BAR_HEIGHT : 0,
          change,
          growthRate: previous ? (change / previous) * 100 : null
        }
      })
    })

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return 'success'
      if (rate >= 75) return 'warning'
      return 'danger'
    }

    const changeClass = (change) => {
      if (change > 0) return 'positive-change'
      if (change < 0) return 'negative-change'
      return ''
    }

    const formatChange = (change) => {
      if (change === 0) return money(0)
      return (change > 0 ? '+' : '-') + money(Math.abs(change))
    }

    const formatGrowth = (rate) => (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'

    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadData()
    })

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyData,
      monthlyRows,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      money,
      formatQuarter,
      getFulfillmentClass,
      changeClass,
      formatChange,
      formatGrowth
    }
  }
}
</script>

<style scoped>
.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.num {
  text-align: right;
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}

.empty-state {
  color: #64748b;
  text-align: center;
  padding: 2rem 1rem;
}
</style>
