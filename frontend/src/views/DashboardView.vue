<template>
  <div>
    <!-- Cartes soldes -->
    <n-grid :cols="isMobile ? 1 : accounts.length > 2 ? 3 : 2" :x-gap="16" :y-gap="16" style="margin-bottom: 24px;">
      <!-- Solde total -->
      <n-grid-item>
        <n-card embedded bordered>
          <n-statistic label="Solde total">
            <template #prefix><span style="font-size: 20px;">💳</span></template>
            <n-number-animation :from="0" :to="totalBalance" :precision="2" />
            <template #suffix>€</template>
          </n-statistic>
          <n-text depth="3" style="font-size: 12px;">
            Dernière sync : {{ lastSyncLabel }}
          </n-text>
        </n-card>
      </n-grid-item>

      <!-- Dépenses du mois -->
      <n-grid-item>
        <n-card embedded bordered>
          <n-statistic label="Dépenses ce mois">
            <template #prefix><span style="font-size: 20px;">📉</span></template>
            <n-number-animation :from="0" :to="monthExpenses" :precision="2" />
            <template #suffix>€</template>
          </n-statistic>
          <n-progress
            type="line"
            :percentage="expenseProgress"
            :color="expenseProgress > 90 ? '#d03050' : '#18a058'"
            :show-indicator="false"
            style="margin-top: 8px;"
          />
        </n-card>
      </n-grid-item>

      <!-- Revenus du mois -->
      <n-grid-item v-if="!isMobile || accounts.length > 0">
        <n-card embedded bordered>
          <n-statistic label="Revenus ce mois">
            <template #prefix><span style="font-size: 20px;">📈</span></template>
            <n-number-animation :from="0" :to="monthIncome" :precision="2" />
            <template #suffix>€</template>
          </n-statistic>
          <n-text :style="{ color: netFlow >= 0 ? '#18a058' : '#d03050', fontSize: '12px' }">
            Solde net : {{ netFlow >= 0 ? '+' : '' }}{{ netFlow.toFixed(2) }} €
          </n-text>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- Graphique + comptes -->
    <n-grid :cols="isMobile ? 1 : 3" :x-gap="16" :y-gap="16" style="margin-bottom: 24px;">
      <!-- Graphique dépenses par catégorie -->
      <n-grid-item :span="2">
        <n-card title="Dépenses par catégorie — ce mois" embedded bordered>
          <div v-if="chartLoading" style="height: 280px; display: flex; align-items: center; justify-content: center;">
            <n-spin />
          </div>
          <div v-else-if="pieData.length === 0" style="height: 280px; display: flex; align-items: center; justify-content: center;">
            <n-empty description="Aucune dépense ce mois" />
          </div>
          <v-chart v-else :option="pieOption" style="height: 280px;" autoresize />
        </n-card>
      </n-grid-item>

      <!-- Comptes bancaires -->
      <n-grid-item>
        <n-card title="Comptes" embedded bordered>
          <n-skeleton v-if="accountsStore.loading" :repeat="2" text style="margin-bottom: 12px;" />
          <div v-for="account in accounts" :key="account.id" style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <n-text strong>{{ account.name }}</n-text><br />
                <n-text depth="3" style="font-size: 12px;">{{ account.number_masked }}</n-text>
              </div>
              <n-text :class="account.balance >= 0 ? 'amount-positive' : 'amount-negative'">
                {{ account.balance.toFixed(2) }} €
              </n-text>
            </div>
            <n-divider style="margin: 8px 0;" />
          </div>
          <n-empty v-if="!accountsStore.loading && accounts.length === 0" description="Aucun compte. Configurez Crédit Agricole dans les Paramètres." size="small" />
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- Budgets -->
    <n-card title="État des budgets" embedded bordered style="margin-bottom: 24px;">
      <template #header-extra>
        <n-button text tag="a" href="/budgets">Gérer →</n-button>
      </template>
      <n-skeleton v-if="budgetsLoading" :repeat="2" text />
      <n-empty v-else-if="budgets.length === 0" description="Aucun budget configuré" size="small" />
      <n-grid v-else :cols="isMobile ? 1 : Math.min(budgets.length, 3)" :x-gap="12" :y-gap="8">
        <n-grid-item v-for="b in budgets" :key="b.id">
          <div style="padding: 4px 0;">
            <n-space justify="space-between" align="center">
              <n-text style="font-size: 13px;" strong>{{ b.name }}</n-text>
              <n-text style="font-size: 12px;" :style="{ color: b.target_amount && b.spent > b.target_amount ? '#d03050' : '#18a058' }">
                {{ b.spent.toFixed(2) }} €{{ b.target_amount ? ` / ${b.target_amount.toFixed(2)} €` : '' }}
              </n-text>
            </n-space>
            <n-progress
              v-if="b.target_amount"
              type="line"
              :percentage="Math.min(100, (b.spent / b.target_amount) * 100)"
              :color="b.spent > b.target_amount ? '#d03050' : b.color || '#18a058'"
              :show-indicator="false"
              style="margin-top: 4px;"
            />
            <n-text v-else depth="3" style="font-size: 11px;">{{ b.entry_count }} opération(s)</n-text>
          </div>
        </n-grid-item>
      </n-grid>
    </n-card>

    <!-- Transactions récentes -->
    <n-card title="Transactions récentes" embedded bordered>
      <template #header-extra>
        <n-button text tag="a" href="/transactions">Voir tout →</n-button>
      </template>

      <n-skeleton v-if="txLoading" :repeat="5" text style="margin-bottom: 8px;" />
      <n-empty v-else-if="recentTransactions.length === 0" description="Aucune transaction" />
      <div v-else>
        <div
          v-for="tx in recentTransactions"
          :key="tx.id"
          style="display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--n-border-color);"
        >
          <div style="flex: 1; min-width: 0;">
            <n-text style="font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block;">
              {{ tx.label }}
            </n-text>
            <n-text depth="3" style="font-size: 12px;">
              {{ formatDate(tx.date) }}
              <n-tag v-if="tx.category_name" size="tiny" :bordered="false" style="margin-left: 6px;">
                {{ tx.category_name }}
              </n-tag>
            </n-text>
          </div>
          <n-text :class="tx.amount >= 0 ? 'amount-positive' : 'amount-negative'" style="margin-left: 16px; white-space: nowrap;">
            {{ tx.amount >= 0 ? '+' : '' }}{{ tx.amount.toFixed(2) }} €
          </n-text>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import { format, startOfMonth } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useAccountsStore } from '@/stores/accounts'
import { useTransactionsStore } from '@/stores/transactions'
import { useBudgetsStore } from '@/stores/budgets'

use([PieChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')
const accountsStore = useAccountsStore()
const txStore = useTransactionsStore()

const txLoading = ref(true)
const chartLoading = ref(true)
const budgetsLoading = ref(true)

const budgetsStore = useBudgetsStore()
const budgets = computed(() => budgetsStore.budgets)
const accounts = computed(() => accountsStore.accounts)
const totalBalance = computed(() => accountsStore.totalBalance)
const recentTransactions = computed(() => txStore.transactions.slice(0, 10))

// Calculs mensuels
const monthStart = format(startOfMonth(new Date()), 'yyyy-MM-dd')
const monthTransactions = computed(() =>
  txStore.transactions.filter((t) => t.date >= monthStart)
)
const monthExpenses = computed(() =>
  Math.abs(monthTransactions.value.filter((t) => t.amount < 0).reduce((s, t) => s + t.amount, 0))
)
const monthIncome = computed(() =>
  monthTransactions.value.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0)
)
const netFlow = computed(() => monthIncome.value - monthExpenses.value)
const expenseProgress = computed(() =>
  monthIncome.value > 0 ? Math.min(100, (monthExpenses.value / monthIncome.value) * 100) : 0
)

const lastSyncLabel = computed(() => {
  const synced = accounts.value.map((a) => a.last_synced).filter(Boolean)
  if (synced.length === 0) return 'Jamais'
  const sorted = synced.sort(); const latest = sorted[sorted.length - 1]!
  return format(new Date(latest), 'dd/MM à HH:mm', { locale: fr })
})

// Données graphique camembert
const pieData = computed(() => {
  const byCategory: Record<string, number> = {}
  monthTransactions.value
    .filter((t) => t.amount < 0)
    .forEach((t) => {
      const cat = t.category_name ?? 'Non catégorisé'
      byCategory[cat] = (byCategory[cat] ?? 0) + Math.abs(t.amount)
    })
  return Object.entries(byCategory)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, value]) => ({ name, value: parseFloat(value.toFixed(2)) }))
})

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} € ({d}%)' },
  legend: { orient: 'vertical', right: 10, top: 'center', type: 'scroll' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['40%', '50%'],
    avoidLabelOverlap: true,
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
    data: pieData.value,
  }],
}))

function formatDate(d: string) {
  return format(new Date(d), 'dd MMM yyyy', { locale: fr })
}

onMounted(async () => {
  await Promise.all([
    accountsStore.fetchAccounts(),
    txStore.fetchTransactions({ limit: 50, date_from: monthStart }),
    budgetsStore.fetchBudgets().finally(() => { budgetsLoading.value = false }),
  ])
  txLoading.value = false
  chartLoading.value = false
})
</script>
