<template>
  <div style="display: flex; flex-direction: column; height: calc(100vh - 120px);">
    <!-- Messages -->
    <n-scrollbar ref="scrollbarRef" style="flex: 1;">
      <div style="padding: 8px;">
        <!-- Message d'accueil -->
        <div v-if="messages.length === 0" style="text-align: center; padding: 60px 20px;">
          <div style="font-size: 48px; margin-bottom: 16px;">🤖</div>
          <n-h3>Assistant bancaire IA</n-h3>
          <n-text depth="3">
            Posez-moi des questions sur vos finances. Par exemple :<br />
            « Combien j'ai dépensé en restaurants ce mois ? »<br />
            « Quel est mon budget restant cette semaine ? »<br />
            « Génère-moi un rapport de mes dépenses en 2024 »
          </n-text>

          <!-- Suggestions rapides -->
          <n-space justify="center" style="margin-top: 24px; flex-wrap: wrap;">
            <n-button
              v-for="s in suggestions"
              :key="s"
              size="small"
              @click="sendMessage(s)"
            >
              {{ s }}
            </n-button>
          </n-space>
        </div>

        <!-- Bulles de messages -->
        <div v-for="msg in messages" :key="msg.id" style="margin-bottom: 16px;" :style="{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }">
          <div :style="{
            maxWidth: '80%',
            padding: '12px 16px',
            borderRadius: '12px',
            background: msg.role === 'user' ? '#18a058' : 'var(--n-card-color)',
            color: msg.role === 'user' ? 'white' : 'inherit',
            border: msg.role === 'assistant' ? '1px solid var(--n-border-color)' : 'none',
            whiteSpace: 'pre-wrap',
            lineHeight: '1.5',
          }">
            <n-spin v-if="msg.loading" size="small" />
            <span v-else>{{ msg.content }}</span>
          </div>
        </div>
      </div>
    </n-scrollbar>

    <!-- Zone de saisie -->
    <div style="padding: 12px 0; border-top: 1px solid var(--n-border-color);">
      <n-space align="center">
        <n-input
          v-model:value="input"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="Posez une question sur vos finances…"
          :disabled="isLoading"
          style="flex: 1;"
          @keydown.enter.exact.prevent="handleEnter"
        />
        <n-button
          type="primary"
          circle
          :loading="isLoading"
          :disabled="!input.trim()"
          @click="sendMessage()"
        >
          <template #icon>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </template>
        </n-button>
      </n-space>
      <n-text depth="3" style="font-size: 11px; margin-top: 4px;">
        Entrée pour envoyer · Maj+Entrée pour nouvelle ligne
      </n-text>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import api from '@/api/client'
import { useTransactionsStore } from '@/stores/transactions'
import { useAccountsStore } from '@/stores/accounts'
import { format, startOfMonth } from 'date-fns'

const message = useMessage()
const txStore = useTransactionsStore()
const accountsStore = useAccountsStore()

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  loading?: boolean
}

const messages = ref<Message[]>([])
const input = ref('')
const isLoading = ref(false)
const scrollbarRef = ref()

const suggestions = [
  '📊 Résumé du mois',
  '🍽️ Dépenses restaurants ce mois',
  '💡 Conseils pour économiser',
  '📈 Prévision fin de mois',
]

function handleEnter(e: KeyboardEvent) {
  if (!e.shiftKey) sendMessage()
}

async function sendMessage(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || isLoading.value) return

  input.value = ''

  const userMsg: Message = { id: Date.now().toString(), role: 'user', content }
  messages.value.push(userMsg)

  const assistantMsg: Message = { id: (Date.now() + 1).toString(), role: 'assistant', content: '', loading: true }
  messages.value.push(assistantMsg)

  await scrollToBottom()
  isLoading.value = true

  try {
    // Contexte financier injecté dans le prompt
    const context = buildContext()
    const { data } = await api.post('/ai/chat', { message: content, context })
    assistantMsg.content = data.response
    assistantMsg.loading = false
  } catch (e: any) {
    assistantMsg.content = e?.response?.data?.detail ?? 'Désolé, une erreur est survenue. Vérifiez la configuration de l\'IA dans les Paramètres.'
    assistantMsg.loading = false
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

function buildContext(): string {
  const accounts = accountsStore.accounts
  const now = new Date()
  const monthStart = format(startOfMonth(now), 'yyyy-MM-dd')
  const monthTx = txStore.transactions.filter((t) => t.date >= monthStart)
  const expenses = monthTx.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0)
  const income = monthTx.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0)

  const recentTx = txStore.transactions
    .slice(0, 20)
    .map((t) => `${t.date} | ${t.label} | ${t.amount.toFixed(2)}€ | ${t.category_name ?? 'Non catégorisé'}`)
    .join('\n')

  return `## Contexte financier (${format(now, 'dd/MM/yyyy')})

Comptes bancaires:
${accounts.map((a) => `- ${a.name}: ${a.balance.toFixed(2)} €`).join('\n') || 'Aucun compte configuré'}

Mois en cours (${format(now, 'MMMM yyyy')}):
- Revenus: ${income.toFixed(2)} €
- Dépenses: ${expenses.toFixed(2)} €
- Solde net: ${(income - expenses).toFixed(2)} €

20 dernières transactions:
${recentTx || 'Aucune transaction'}

Réponds en français de manière concise et utile.`
}

async function scrollToBottom() {
  await nextTick()
  scrollbarRef.value?.scrollTo({ top: 999999, behavior: 'smooth' })
}
</script>
