<template>
  <div>
    <!-- Filtres -->
    <n-card embedded bordered style="margin-bottom: 16px;">
      <n-grid :cols="isMobile ? 1 : 4" :x-gap="12" :y-gap="12">
        <n-grid-item>
          <n-input
            v-model:value="search"
            placeholder="Rechercher un libellé…"
            clearable
            @update:value="debouncedFetch"
          >
            <template #prefix>🔍</template>
          </n-input>
        </n-grid-item>
        <n-grid-item>
          <n-date-picker
            v-model:value="dateRange"
            type="daterange"
            clearable
            style="width: 100%;"
            @update:value="fetchWithFilters"
          />
        </n-grid-item>
        <n-grid-item>
          <n-select
            v-model:value="selectedCategory"
            :options="categoryOptions"
            placeholder="Catégorie"
            clearable
            @update:value="fetchWithFilters"
          />
        </n-grid-item>
        <n-grid-item>
          <n-select
            v-model:value="selectedAccount"
            :options="accountOptions"
            placeholder="Compte"
            clearable
            @update:value="fetchWithFilters"
          />
        </n-grid-item>
      </n-grid>
    </n-card>

    <!-- Import CSV/OFX -->
    <n-card embedded bordered style="margin-bottom: 16px;">
      <template #header>
        <n-space align="center">
          <span>Import manuel (fallback woob)</span>
          <n-tooltip>
            <template #trigger><n-tag size="tiny" type="warning">📎</n-tag></template>
            Utilisez l'import si le scraping automatique est indisponible
          </n-tooltip>
        </n-space>
      </template>
      <n-space>
        <n-upload accept=".csv" :custom-request="importCSV" :show-file-list="false">
          <n-button size="small">📄 Import CSV</n-button>
        </n-upload>
        <n-upload accept=".ofx,.qfx" :custom-request="importOFX" :show-file-list="false">
          <n-button size="small">📄 Import OFX</n-button>
        </n-upload>
      </n-space>
    </n-card>

    <!-- Résumé -->
    <n-space style="margin-bottom: 12px;">
      <n-tag type="default">{{ txStore.transactions.length }} transaction(s)</n-tag>
      <n-tag type="error">Dépenses : {{ totalExpenses.toFixed(2) }} €</n-tag>
      <n-tag type="success">Revenus : {{ totalIncome.toFixed(2) }} €</n-tag>
    </n-space>

    <!-- Table -->
    <n-data-table
      :columns="columns"
      :data="txStore.transactions"
      :loading="txStore.loading"
      :pagination="{ pageSize: 50 }"
      :row-key="(row) => row.id"
      size="small"
      striped
    />

    <!-- Modal catégorisation -->
    <n-modal v-model:show="showCategorizeModal" preset="card" title="Catégoriser la transaction" style="width: 420px;">
      <div v-if="selectedTx">
        <n-text strong>{{ selectedTx.label }}</n-text><br />
        <n-text depth="3">{{ selectedTx.date }} — {{ selectedTx.amount.toFixed(2) }} €</n-text>
        <n-form style="margin-top: 16px;">
          <n-form-item label="Catégorie">
            <n-select v-model:value="editCategory" :options="categoryOptions" clearable />
          </n-form-item>
          <n-form-item label="Notes">
            <n-input v-model:value="editNotes" type="textarea" placeholder="Note libre…" :rows="2" />
          </n-form-item>
        </n-form>
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCategorizeModal = false">Annuler</n-button>
          <n-button type="primary" :loading="saving" @click="saveCategory">Enregistrer</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useMessage } from 'naive-ui'
import { useBreakpoints, breakpointsTailwind, useDebounceFn } from '@vueuse/core'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import type { DataTableColumns } from 'naive-ui'
import { useTransactionsStore } from '@/stores/transactions'
import { useAccountsStore } from '@/stores/accounts'
import api from '@/api/client'
import type { Transaction } from '@/api/transactions'

const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')
const txStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const message = useMessage()

const search = ref('')
const dateRange = ref<[number, number] | null>(null)
const selectedCategory = ref<string | null>(null)
const selectedAccount = ref<string | null>(null)

const showCategorizeModal = ref(false)
const selectedTx = ref<Transaction | null>(null)
const editCategory = ref<string | null>(null)
const editNotes = ref('')
const saving = ref(false)

const categories = ref<{ id: string; name: string }[]>([])

const categoryOptions = computed(() => [
  { label: '— Toutes —', value: null },
  ...categories.value.map((c) => ({ label: c.name, value: c.id })),
])
const accountOptions = computed(() => [
  { label: '— Tous —', value: null },
  ...accountsStore.accounts.map((a) => ({ label: a.name, value: a.id })),
])

const totalExpenses = computed(() =>
  txStore.transactions.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0)
)
const totalIncome = computed(() =>
  txStore.transactions.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0)
)

const columns: DataTableColumns<Transaction> = [
  {
    title: 'Date',
    key: 'date',
    width: 110,
    render: (row) => format(new Date(row.date), 'dd/MM/yyyy', { locale: fr }),
    sorter: (a, b) => a.date.localeCompare(b.date),
  },
  {
    title: 'Libellé',
    key: 'label',
    ellipsis: { tooltip: true },
  },
  {
    title: 'Catégorie',
    key: 'category_name',
    width: 150,
    render: (row) => row.category_name
      ? h('n-tag', { size: 'tiny', bordered: false }, { default: () => row.category_name })
      : h('span', { style: { color: '#999', fontSize: '12px' } }, '—'),
  },
  {
    title: 'Montant',
    key: 'amount',
    width: 120,
    align: 'right',
    sorter: (a, b) => a.amount - b.amount,
    render: (row) =>
      h(
        'span',
        { class: row.amount >= 0 ? 'amount-positive' : 'amount-negative' },
        `${row.amount >= 0 ? '+' : ''}${row.amount.toFixed(2)} €`
      ),
  },
  {
    title: '',
    key: 'actions',
    width: 60,
    render: (row) =>
      h(
        'n-button',
        { size: 'tiny', quaternary: true, onClick: () => openCategorize(row) },
        { default: () => '✏️' }
      ),
  },
]

function openCategorize(tx: Transaction) {
  selectedTx.value = tx
  editCategory.value = tx.category_id
  editNotes.value = tx.notes ?? ''
  showCategorizeModal.value = true
}

async function saveCategory() {
  if (!selectedTx.value) return
  saving.value = true
  try {
    await txStore.updateTransaction(selectedTx.value.id, {
      category_id: editCategory.value,
      notes: editNotes.value || null,
    })
    showCategorizeModal.value = false
    message.success('Transaction mise à jour')
  } catch {
    message.error('Erreur lors de la mise à jour')
  } finally {
    saving.value = false
  }
}

async function fetchWithFilters() {
  const filters: Record<string, unknown> = { limit: 200 }
  if (search.value) filters.search = search.value
  if (selectedCategory.value) filters.category_id = selectedCategory.value
  if (selectedAccount.value) filters.account_id = selectedAccount.value
  if (dateRange.value) {
    filters.date_from = format(new Date(dateRange.value[0]), 'yyyy-MM-dd')
    filters.date_to = format(new Date(dateRange.value[1]), 'yyyy-MM-dd')
  }
  await txStore.fetchTransactions(filters)
}

const debouncedFetch = useDebounceFn(fetchWithFilters, 400)

async function importCSV({ file, onFinish, onError }: any) {
  const form = new FormData()
  form.append('file', file.file)
  try {
    const { data } = await api.post('/scraper/import/csv', form)
    message.success(data.message)
    onFinish()
    fetchWithFilters()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur import CSV')
    onError()
  }
}

async function importOFX({ file, onFinish, onError }: any) {
  const form = new FormData()
  form.append('file', file.file)
  try {
    const { data } = await api.post('/scraper/import/ofx', form)
    message.success(data.message)
    onFinish()
    fetchWithFilters()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur import OFX')
    onError()
  }
}

onMounted(async () => {
  await Promise.all([
    txStore.fetchTransactions({ limit: 100 }),
    accountsStore.fetchAccounts(),
    api.get('/categories/').then(({ data }) => { categories.value = data }).catch(() => {}),
  ])
})
</script>
