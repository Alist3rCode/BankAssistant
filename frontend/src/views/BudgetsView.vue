<template>
  <div>
    <!-- En-tête -->
    <n-space justify="space-between" align="center" style="margin-bottom: 16px;">
      <n-h3 style="margin: 0;">Gestion des budgets</n-h3>
      <n-button type="primary" @click="openCreateModal()">➕ Nouveau budget</n-button>
    </n-space>

    <!-- Cartes budgets -->
    <n-skeleton v-if="budgetsStore.loading" :repeat="3" style="height: 140px; margin-bottom: 16px;" />

    <n-grid v-else :cols="isMobile ? 1 : 3" :x-gap="16" :y-gap="16">
      <n-grid-item v-for="budget in budgetsStore.budgets" :key="budget.id">
        <n-card
          embedded
          :bordered="true"
          :style="{ borderLeft: `4px solid ${budget.color || '#18a058'}` }"
          hoverable
          @click="openDetail(budget)"
          style="cursor: pointer;"
        >
          <n-space justify="space-between" align="center">
            <div>
              <n-text strong style="font-size: 16px;">{{ budget.name }}</n-text>
              <n-tag v-if="budget.is_default" size="tiny" type="success" style="margin-left: 8px;">Principal</n-tag>
            </div>
            <n-button size="tiny" quaternary circle @click.stop="openCreateModal(budget)">✏️</n-button>
          </n-space>

          <n-text v-if="budget.description" depth="3" style="font-size: 12px; display: block; margin: 4px 0;">
            {{ budget.description }}
          </n-text>

          <!-- Stats -->
          <div style="margin-top: 12px;">
            <n-space justify="space-between" align="center" style="margin-bottom: 4px;">
              <n-text depth="3" style="font-size: 12px;">
                {{ budget.entry_count }} opération(s)
              </n-text>
              <n-text v-if="budget.target_amount" depth="3" style="font-size: 12px;">
                / {{ budget.target_amount.toFixed(2) }} €
              </n-text>
            </n-space>

            <n-space>
              <n-text strong style="font-size: 18px;" :style="{ color: budget.spent > (budget.target_amount ?? Infinity) ? '#d03050' : '#333' }">
                {{ budget.spent.toFixed(2) }} €
              </n-text>
              <n-tag v-if="budget.income > 0" type="success" size="tiny">+{{ budget.income.toFixed(2) }} €</n-tag>
            </n-space>

            <n-progress
              v-if="budget.target_amount"
              type="line"
              :percentage="Math.min(100, (budget.spent / budget.target_amount) * 100)"
              :color="budget.spent > budget.target_amount ? '#d03050' : budget.color || '#18a058'"
              :show-indicator="false"
              style="margin-top: 6px;"
            />
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- Modal détail budget (assignations) -->
    <n-modal v-model:show="showDetailModal" preset="card" :title="detailBudget?.name" style="width: 680px; max-width: 98vw;">
      <template #header-extra>
        <n-button size="small" type="primary" @click="openAssignModal">➕ Assigner une transaction</n-button>
      </template>

      <n-spin v-if="entriesLoading" />
      <n-empty v-else-if="entries.length === 0" description="Aucune transaction assignée à ce budget" />
      <n-data-table
        v-else
        :columns="entryColumns"
        :data="entries"
        :bordered="false"
        size="small"
        :max-height="400"
      />
    </n-modal>

    <!-- Modal assignation transaction -->
    <n-modal v-model:show="showAssignModal" preset="card" title="Assigner une transaction" style="width: 560px;">
      <n-form label-placement="top">
        <n-form-item label="Transaction">
          <n-select
            v-model:value="assignForm.transaction_id"
            :options="transactionOptions"
            filterable
            placeholder="Rechercher une transaction…"
            :loading="txLoading"
          />
        </n-form-item>
        <n-form-item label="Montant alloué (laisser 0 = montant total de la transaction)">
          <n-input-number
            v-model:value="assignForm.amount"
            :min="-999999"
            :max="999999"
            :precision="2"
            style="width: 100%;"
          >
            <template #suffix>€</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="Notes">
          <n-input v-model:value="assignForm.notes" placeholder="Note optionnelle…" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAssignModal = false">Annuler</n-button>
          <n-button type="primary" :loading="assignLoading" @click="saveAssign">Assigner</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- Modal création/édition budget -->
    <n-modal v-model:show="showCreateModal" preset="card" :title="editingBudget ? 'Modifier le budget' : 'Nouveau budget'" style="width: 480px;">
      <n-form :model="budgetForm" label-placement="top">
        <n-form-item label="Nom du budget" required>
          <n-input v-model:value="budgetForm.name" placeholder="ex: Vie courante, Voyage Japon…" />
        </n-form-item>
        <n-form-item label="Description">
          <n-input v-model:value="budgetForm.description" placeholder="Description optionnelle" />
        </n-form-item>
        <n-form-item label="Montant cible (laisser vide = illimité)">
          <n-input-number v-model:value="budgetForm.target_amount" :min="0" placeholder="ex: 1500" style="width: 100%;">
            <template #suffix>€</template>
          </n-input-number>
        </n-form-item>
        <n-form-item label="Période">
          <n-select v-model:value="budgetForm.period_type" :options="[
            { label: 'Mensuel', value: 'monthly' },
            { label: 'Annuel', value: 'yearly' },
            { label: 'Ponctuel (sans période)', value: 'none' },
          ]" />
        </n-form-item>
        <n-form-item label="Couleur">
          <n-color-picker v-model:value="budgetForm.color" :modes="['hex']" />
        </n-form-item>
        <n-form-item label="Budget principal (Vie courante)">
          <n-switch v-model:value="budgetForm.is_default" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="space-between">
          <n-popconfirm v-if="editingBudget && !editingBudget.is_default" @positive-click="confirmDelete">
            <template #trigger><n-button type="error" ghost>Supprimer</n-button></template>
            Supprimer ce budget ? Les entrées de transactions seront perdues.
          </n-popconfirm>
          <div v-else />
          <n-space>
            <n-button @click="showCreateModal = false">Annuler</n-button>
            <n-button type="primary" :loading="saving" @click="saveBudget">
              {{ editingBudget ? 'Modifier' : 'Créer' }}
            </n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue'
import { useMessage, NButton, NSpace } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import api from '@/api/client'
import { useBudgetsStore } from '@/stores/budgets'
import type { Budget } from '@/stores/budgets'

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')
const message = useMessage()
const budgetsStore = useBudgetsStore()

// ── Création / édition ────────────────────────────────────────
const showCreateModal = ref(false)
const editingBudget = ref<Budget | null>(null)
const saving = ref(false)
const budgetForm = ref({ name: '', description: '', target_amount: null as number | null, period_type: 'monthly', color: '#18a058', is_default: false })

function openCreateModal(budget?: Budget) {
  editingBudget.value = budget ?? null
  budgetForm.value = {
    name: budget?.name ?? '',
    description: budget?.description ?? '',
    target_amount: budget?.target_amount ?? null,
    period_type: budget?.period_type ?? 'monthly',
    color: budget?.color ?? '#18a058',
    is_default: budget?.is_default ?? false,
  }
  showCreateModal.value = true
}

async function saveBudget() {
  if (!budgetForm.value.name.trim()) { message.warning('Nom requis'); return }
  saving.value = true
  try {
    if (editingBudget.value) {
      await budgetsStore.updateBudget(editingBudget.value.id, budgetForm.value)
      message.success('Budget modifié')
    } else {
      await budgetsStore.createBudget(budgetForm.value)
      message.success('Budget créé')
    }
    showCreateModal.value = false
    await budgetsStore.fetchBudgets()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur')
  } finally {
    saving.value = false
    editingBudget.value = null
  }
}

async function confirmDelete() {
  if (!editingBudget.value) return
  try {
    await budgetsStore.deleteBudget(editingBudget.value.id)
    message.success('Budget supprimé')
    showCreateModal.value = false
  } catch {
    message.error('Erreur lors de la suppression')
  }
}

// ── Détail budget (entrées) ───────────────────────────────────
const showDetailModal = ref(false)
const detailBudget = ref<Budget | null>(null)
const entries = ref<any[]>([])
const entriesLoading = ref(false)

async function openDetail(budget: Budget) {
  detailBudget.value = budget
  showDetailModal.value = true
  entriesLoading.value = true
  try {
    const { data } = await api.get(`/budgets/${budget.id}/entries`)
    entries.value = data
  } finally {
    entriesLoading.value = false
  }
}

const entryColumns: DataTableColumns<any> = [
  { title: 'Date', key: 'transaction_date', width: 100, render: (r) => format(new Date(r.transaction_date), 'dd/MM/yy', { locale: fr }) },
  { title: 'Transaction', key: 'transaction_label', ellipsis: { tooltip: true } },
  {
    title: 'Tx. originale',
    key: 'transaction_amount',
    width: 110,
    align: 'right',
    render: (r) => h('span', { class: r.transaction_amount >= 0 ? 'amount-positive' : 'amount-negative' },
      `${r.transaction_amount >= 0 ? '+' : ''}${r.transaction_amount.toFixed(2)} €`),
  },
  {
    title: 'Montant alloué',
    key: 'amount',
    width: 120,
    align: 'right',
    render: (r) => h('span', { class: r.amount >= 0 ? 'amount-positive' : 'amount-negative' },
      `${r.amount >= 0 ? '+' : ''}${r.amount.toFixed(2)} €`),
  },
  { title: 'Notes', key: 'notes', ellipsis: { tooltip: true } },
  {
    title: '',
    key: 'actions',
    width: 50,
    render: (r) => h(NButton, {
      size: 'tiny', type: 'error', quaternary: true,
      onClick: () => removeEntry(r.id),
    }, { default: () => '🗑️' }),
  },
]

async function removeEntry(entryId: string) {
  if (!detailBudget.value) return
  try {
    await api.delete(`/budgets/${detailBudget.value.id}/entries/${entryId}`)
    entries.value = entries.value.filter(e => e.id !== entryId)
    await budgetsStore.fetchBudgets()
    message.success('Entrée supprimée')
  } catch {
    message.error('Erreur lors de la suppression')
  }
}

// ── Assignation transaction ───────────────────────────────────
const showAssignModal = ref(false)
const assignLoading = ref(false)
const txLoading = ref(false)
const availableTransactions = ref<any[]>([])
const assignForm = ref({ transaction_id: '', amount: 0, notes: '' })

const transactionOptions = computed(() =>
  availableTransactions.value.map(t => ({
    label: `${t.date} | ${t.label} | ${t.amount > 0 ? '+' : ''}${t.amount.toFixed(2)} €`,
    value: t.id,
  }))
)

async function openAssignModal() {
  showAssignModal.value = true
  assignForm.value = { transaction_id: '', amount: 0, notes: '' }
  txLoading.value = true
  try {
    const { data } = await api.get('/transactions/', { params: { limit: 200 } })
    availableTransactions.value = data
  } finally {
    txLoading.value = false
  }
}

async function saveAssign() {
  if (!detailBudget.value || !assignForm.value.transaction_id) {
    message.warning('Sélectionnez une transaction')
    return
  }
  assignLoading.value = true
  try {
    await api.post(`/budgets/${detailBudget.value.id}/entries`, assignForm.value)
    message.success('Transaction assignée')
    showAssignModal.value = false
    await openDetail(detailBudget.value)
    await budgetsStore.fetchBudgets()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur')
  } finally {
    assignLoading.value = false
  }
}

onMounted(() => budgetsStore.fetchBudgets())
</script>
