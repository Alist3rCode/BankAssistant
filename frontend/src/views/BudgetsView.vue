<template>
  <div>
    <!-- En-tête + bouton création -->
    <n-space justify="space-between" align="center" style="margin-bottom: 16px;">
      <n-h3 style="margin: 0;">Gestion des budgets</n-h3>
      <n-button type="primary" @click="showCreateModal = true">
        ➕ Nouveau budget
      </n-button>
    </n-space>

    <!-- Cartes budgets -->
    <n-skeleton v-if="loading" :repeat="3" style="height: 120px; margin-bottom: 16px;" />

    <n-grid v-else :cols="isMobile ? 1 : 3" :x-gap="16" :y-gap="16">
      <n-grid-item v-for="budget in budgets" :key="budget.id">
        <n-card embedded :bordered="true" :style="{ borderLeft: `4px solid ${budget.color || '#18a058'}` }">
          <n-space justify="space-between" align="center">
            <div>
              <n-text strong style="font-size: 16px;">{{ budget.name }}</n-text>
              <n-tag v-if="budget.is_default" size="tiny" type="success" style="margin-left: 8px;">Principal</n-tag>
            </div>
            <n-button size="tiny" quaternary circle @click="editBudget(budget)">✏️</n-button>
          </n-space>

          <n-text depth="3" style="font-size: 12px;">{{ budget.description }}</n-text>

          <div style="margin-top: 12px;">
            <n-space justify="space-between">
              <n-text depth="3" style="font-size: 12px;">Dépenses</n-text>
              <n-text v-if="budget.target_amount" depth="3" style="font-size: 12px;">
                / {{ budget.target_amount.toFixed(2) }} €
              </n-text>
            </n-space>
            <n-text strong style="font-size: 20px; color: #d03050;">
              {{ getBudgetSpent(budget.id).toFixed(2) }} €
            </n-text>
            <n-progress
              v-if="budget.target_amount"
              type="line"
              :percentage="Math.min(100, (getBudgetSpent(budget.id) / budget.target_amount) * 100)"
              :color="getBudgetSpent(budget.id) > budget.target_amount ? '#d03050' : budget.color || '#18a058'"
              :show-indicator="false"
              style="margin-top: 4px;"
            />
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- Création/édition budget -->
    <n-modal v-model:show="showCreateModal" preset="card" :title="editingBudget ? 'Modifier le budget' : 'Nouveau budget'" style="width: 480px;">
      <n-form ref="budgetFormRef" :model="budgetForm" label-placement="top">
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
          <n-select
            v-model:value="budgetForm.period_type"
            :options="[
              { label: 'Mensuel', value: 'monthly' },
              { label: 'Annuel', value: 'yearly' },
              { label: 'Ponctuel (sans période)', value: 'none' },
            ]"
          />
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
          <n-popconfirm v-if="editingBudget && !editingBudget.is_default" @positive-click="deleteBudget">
            <template #trigger><n-button type="error" ghost>Supprimer</n-button></template>
            Supprimer ce budget ? Les affectations de transactions seront perdues.
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
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import api from '@/api/client'

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')
const message = useMessage()

const budgets = ref<any[]>([])
const budgetEntries = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)
const showCreateModal = ref(false)
const editingBudget = ref<any | null>(null)

const budgetForm = ref({
  name: '', description: '', target_amount: null as number | null,
  period_type: 'monthly', color: '#18a058', is_default: false,
})

function getBudgetSpent(budgetId: string): number {
  return budgetEntries.value
    .filter((e) => e.budget_id === budgetId && e.amount < 0)
    .reduce((s: number, e: any) => s + Math.abs(e.amount), 0)
}

function editBudget(budget: any) {
  editingBudget.value = budget
  budgetForm.value = {
    name: budget.name,
    description: budget.description ?? '',
    target_amount: budget.target_amount,
    period_type: budget.period_type,
    color: budget.color ?? '#18a058',
    is_default: budget.is_default,
  }
  showCreateModal.value = true
}

async function saveBudget() {
  if (!budgetForm.value.name) return
  saving.value = true
  try {
    if (editingBudget.value) {
      await api.put(`/budgets/${editingBudget.value.id}`, budgetForm.value)
      message.success('Budget modifié')
    } else {
      await api.post('/budgets/', budgetForm.value)
      message.success('Budget créé')
    }
    showCreateModal.value = false
    await loadBudgets()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur')
  } finally {
    saving.value = false
    editingBudget.value = null
  }
}

async function deleteBudget() {
  if (!editingBudget.value) return
  try {
    await api.delete(`/budgets/${editingBudget.value.id}`)
    message.success('Budget supprimé')
    showCreateModal.value = false
    await loadBudgets()
  } catch {
    message.error('Erreur lors de la suppression')
  }
}

async function loadBudgets() {
  const { data } = await api.get('/budgets/')
  budgets.value = data
}

onMounted(async () => {
  loading.value = true
  try {
    await loadBudgets()
  } finally {
    loading.value = false
  }
})
</script>
