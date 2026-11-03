<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-header">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
          <span class="budget-value">{{ money(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="sliderMax"
          step="500"
        />
        <div class="budget-hint">{{ t('restocking.budgetHint', { max: money(plan.max_budget) }) }}</div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.plannedSpend') }}</div>
          <div class="stat-value">{{ money(plan.total_cost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ money(Math.max(budget - plan.total_cost, 0)) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.itemsPlanned') }}</div>
          <div class="stat-value">{{ plan.items.length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ plan.items.length }})</h3>
            <div class="ranking-note">{{ t('restocking.rankingNote') }}</div>
          </div>
          <button
            class="place-order-btn"
            :disabled="plan.items.length === 0 || placing || planLoading"
            @click="placeOrder"
          >
            {{ placing ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="orderMessage" :class="['order-message', orderMessage.type]">
          {{ orderMessage.text }}
          <router-link v-if="orderMessage.type === 'success'" to="/orders">{{ t('restocking.viewOrders') }}</router-link>
        </div>

        <div v-if="plan.items.length === 0" class="empty-state">{{ t('restocking.noItems') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in plan.items" :key="item.item_sku">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>
                  {{ translateProductName(item.item_name) }}
                  <span v-if="item.has_backlog" class="badge danger">{{ t('restocking.backlog') }}</span>
                  <span v-if="isPartial(item)" class="badge warning">{{ t('restocking.partial') }}</span>
                </td>
                <td><span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span></td>
                <td class="num">{{ item.quantity.toLocaleString() }}</td>
                <td class="num">{{ money(item.unit_cost, 2) }}</td>
                <td class="num"><strong>{{ money(item.line_total, 2) }}</strong></td>
                <td class="num">{{ t('restocking.table.days', { count: item.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const BUDGET_STEP = 500

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const planLoading = ref(false)
    const error = ref(null)
    const budget = ref(0)
    const plan = ref({ budget: 0, max_budget: 0, total_cost: 0, items: [] })
    const fullQuantities = ref({})
    const placing = ref(false)
    const orderMessage = ref(null)
    let debounceTimer = null

    // Round the slider max up to a whole step so the full plan is always reachable
    const sliderMax = computed(() => Math.ceil(plan.value.max_budget / BUDGET_STEP) * BUDGET_STEP)

    const money = (amount, decimals = 0) => formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    const isPartial = (item) => item.quantity < (fullQuantities.value[item.item_sku] ?? item.quantity)

    const loadPlan = async () => {
      try {
        planLoading.value = true
        plan.value = await api.getRestockPlan(budget.value)
      } catch (err) {
        error.value = 'Failed to load restocking plan: ' + err.message
      } finally {
        planLoading.value = false
      }
    }

    const init = async () => {
      try {
        loading.value = true
        error.value = null
        // Without a budget the API returns the full plan; keep its quantities to flag partial lines
        const fullPlan = await api.getRestockPlan()
        fullQuantities.value = Object.fromEntries(fullPlan.items.map(i => [i.item_sku, i.quantity]))
        plan.value = fullPlan
        budget.value = Math.round(fullPlan.max_budget / 2 / BUDGET_STEP) * BUDGET_STEP
        await loadPlan()
      } catch (err) {
        error.value = 'Failed to load restocking plan: ' + err.message
      } finally {
        loading.value = false
      }
    }

    watch(budget, () => {
      // init() sets the default budget and loads its plan itself
      if (loading.value) return
      orderMessage.value = null
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadPlan, 200)
    })

    const placeOrder = async () => {
      try {
        placing.value = true
        const order = await api.createRestockOrder(budget.value)
        orderMessage.value = {
          type: 'success',
          text: t('restocking.orderPlaced', { number: order.order_number, days: order.lead_time_days })
        }
      } catch (err) {
        const message = err.response?.data?.detail || err.message
        orderMessage.value = { type: 'error', text: t('restocking.orderFailed', { message }) }
      } finally {
        placing.value = false
      }
    }

    onMounted(init)
    onUnmounted(() => clearTimeout(debounceTimer))

    return {
      t,
      loading,
      planLoading,
      error,
      budget,
      plan,
      sliderMax,
      placing,
      orderMessage,
      money,
      isPartial,
      placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.5rem;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.budget-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
}

.budget-hint,
.ranking-note {
  color: #64748b;
  font-size: 0.813rem;
  margin-top: 0.375rem;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.625rem 1.25rem;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s ease;
  white-space: nowrap;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.order-message {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.order-message a {
  margin-left: 0.5rem;
  font-weight: 600;
  color: inherit;
}

.order-message.success {
  background: #dcfce7;
  color: #166534;
}

.order-message.error {
  background: #fee2e2;
  color: #991b1b;
}

.empty-state {
  color: #64748b;
  text-align: center;
  padding: 2rem 1rem;
}

.num {
  text-align: right;
}

td .badge {
  margin-left: 0.375rem;
}
</style>
