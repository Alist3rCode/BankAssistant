<template>
  <div>
    <n-tabs type="line" animated>

      <!-- ══════════════════════════════════════
           Onglet : Crédit Agricole
      ══════════════════════════════════════ -->
      <n-tab-pane name="ca" tab="🏦 Crédit Agricole">
        <n-card embedded bordered style="margin-top: 16px;">
          <n-form ref="caFormRef" :model="caForm" label-placement="top">
            <n-form-item label="Caisse régionale" path="region">
              <n-select
                v-model:value="caForm.region"
                :options="regionOptions"
                placeholder="Choisissez votre caisse régionale CA"
                filterable
              />
            </n-form-item>
            <n-form-item label="Numéro de compte / identifiant" path="login">
              <n-input v-model:value="caForm.login" placeholder="Votre numéro de compte CA" />
            </n-form-item>
            <n-form-item label="Code confidentiel (6 chiffres)" path="password">
              <n-input
                v-model:value="caForm.password"
                type="password"
                show-password-on="click"
                placeholder="••••••"
                maxlength="6"
              />
            </n-form-item>

            <n-alert type="warning" :bordered="false" style="margin-bottom: 16px;">
              Vos identifiants sont chiffrés (Fernet) avant stockage. Ils ne quittent jamais votre serveur.
            </n-alert>

            <n-space>
              <n-button type="primary" :loading="caLoading" @click="saveCASettings">
                💾 Enregistrer
              </n-button>
              <n-button :loading="testLoading" @click="testCAConnection">
                🔌 Tester la connexion
              </n-button>
            </n-space>
          </n-form>

          <!-- Résultat du test -->
          <n-alert v-if="testResult" :type="testResult.success ? 'success' : 'error'" :bordered="false" style="margin-top: 16px;">
            {{ testResult.message }}
          </n-alert>
        </n-card>

        <n-card embedded bordered style="margin-top: 16px;" title="Scraping automatique">
          <n-form label-placement="left" :label-width="240">
            <n-form-item label="Activer le scraping journalier">
              <n-switch v-model:value="scrapingEnabled" @update:value="saveScraping" />
            </n-form-item>
            <n-form-item label="Heure de synchronisation">
              <n-time-picker
                v-model:value="scrapingTime"
                format="HH:mm"
                :disabled="!scrapingEnabled"
                @update:value="saveScraping"
              />
            </n-form-item>
          </n-form>

          <n-space style="margin-top: 8px;">
            <n-button type="primary" :loading="syncLoading" @click="triggerSyncNow">
              ▶️ Synchroniser maintenant
            </n-button>
            <n-tag v-if="syncStatus" :type="syncStatus === 'idle' ? 'success' : syncStatus === 'running' ? 'warning' : 'error'">
              {{ syncStatus === 'idle' ? '✅ Inactif' : syncStatus === 'running' ? '⏳ En cours...' : '❌ Erreur' }}
            </n-tag>
          </n-space>
        </n-card>
      </n-tab-pane>

      <!-- ══════════════════════════════════════
           Onglet : IA
      ══════════════════════════════════════ -->
      <n-tab-pane name="ai" tab="🤖 Intelligence Artificielle">
        <n-card embedded bordered style="margin-top: 16px;">
          <n-form label-placement="top">
            <n-form-item label="Provider IA">
              <n-radio-group v-model:value="aiForm.provider" @update:value="saveAISettings">
                <n-radio-button value="groq">Groq (recommandé)</n-radio-button>
                <n-radio-button value="mistral">Mistral</n-radio-button>
                <n-radio-button value="ollama">Ollama (local)</n-radio-button>
              </n-radio-group>
            </n-form-item>

            <n-alert v-if="aiForm.provider === 'groq'" type="info" :bordered="false" style="margin-bottom: 16px;">
              Groq offre 1 000 requêtes/jour gratuitement. Créez un compte sur <n-a href="https://console.groq.com" target="_blank">console.groq.com</n-a>
            </n-alert>
            <n-alert v-if="aiForm.provider === 'ollama'" type="warning" :bordered="false" style="margin-bottom: 16px;">
              Ollama nécessite un GPU ou est très lent sur CPU seul. Assurez-vous qu'Ollama tourne sur votre machine hôte.
            </n-alert>

            <n-form-item v-if="aiForm.provider === 'groq'" label="Clé API Groq">
              <n-input
                v-model:value="aiForm.groqKey"
                type="password"
                show-password-on="click"
                placeholder="gsk_..."
              />
            </n-form-item>
            <n-form-item v-if="aiForm.provider === 'mistral'" label="Clé API Mistral">
              <n-input
                v-model:value="aiForm.mistralKey"
                type="password"
                show-password-on="click"
                placeholder="..."
              />
            </n-form-item>
            <n-form-item v-if="aiForm.provider === 'ollama'" label="URL Ollama">
              <n-input v-model:value="aiForm.ollamaUrl" placeholder="http://host.docker.internal:11434" />
            </n-form-item>

            <n-form-item label="Modèle">
              <n-input v-model:value="aiForm.model" :placeholder="defaultModelPlaceholder" />
            </n-form-item>

            <n-form-item label="Catégorisation automatique">
              <n-space>
                <n-switch v-model:value="aiForm.autoCategorize" />
                <n-text depth="3">Catégoriser automatiquement les nouvelles transactions par IA</n-text>
              </n-space>
            </n-form-item>

            <n-button type="primary" :loading="aiLoading" @click="saveAISettings">
              💾 Enregistrer
            </n-button>
          </n-form>
        </n-card>
      </n-tab-pane>

      <!-- ══════════════════════════════════════
           Onglet : Notifications
      ══════════════════════════════════════ -->
      <n-tab-pane name="notif" tab="🔔 Notifications">
        <n-card embedded bordered style="margin-top: 16px;">
          <n-alert type="info" :bordered="false" style="margin-bottom: 20px;">
            Les notifications utilisent <strong>ntfy</strong> (self-hosted). Installez l'app ntfy sur Android depuis le Play Store ou F-Droid, puis abonnez-vous au topic ci-dessous.
          </n-alert>

          <n-form label-placement="left" :label-width="280">
            <n-form-item label="Activer les notifications push">
              <n-switch v-model:value="notifForm.enabled" @update:value="saveNotifSettings" />
            </n-form-item>
            <n-form-item label="URL serveur ntfy">
              <n-input v-model:value="notifForm.url" placeholder="http://votre-ip:2586" :disabled="!notifForm.enabled" />
            </n-form-item>
            <n-form-item label="Topic ntfy">
              <n-input-group>
                <n-input v-model:value="notifForm.topic" :disabled="!notifForm.enabled" />
                <n-button :disabled="!notifForm.enabled" @click="sendTestNotification">
                  Test 🔔
                </n-button>
              </n-input-group>
            </n-form-item>
            <n-form-item label="Alerte dépassement budget">
              <n-switch v-model:value="notifForm.budgetAlert" :disabled="!notifForm.enabled" @update:value="saveNotifSettings" />
            </n-form-item>
            <n-form-item label="Alerte grosse transaction (€)">
              <n-input-number
                v-model:value="notifForm.largeTransactionThreshold"
                :disabled="!notifForm.enabled"
                :min="0"
                placeholder="500"
                style="width: 150px;"
              />
            </n-form-item>
            <n-form-item label="Rapport journalier">
              <n-space>
                <n-switch v-model:value="notifForm.dailyReport" :disabled="!notifForm.enabled" @update:value="saveNotifSettings" />
                <n-time-picker
                  v-if="notifForm.dailyReport"
                  v-model:value="notifForm.dailyReportTime"
                  format="HH:mm"
                  style="width: 120px;"
                />
              </n-space>
            </n-form-item>
          </n-form>

          <n-button type="primary" :loading="notifLoading" @click="saveNotifSettings">
            💾 Enregistrer les notifications
          </n-button>
        </n-card>
      </n-tab-pane>

      <!-- ══════════════════════════════════════
           Onglet : Catégories & Règles
      ══════════════════════════════════════ -->
      <n-tab-pane name="categories" tab="🏷️ Catégories">

        <!-- Catégories -->
        <n-card embedded bordered style="margin-top: 16px;" title="Catégories">
          <template #header-extra>
            <n-button size="small" type="primary" @click="openCategoryModal()">+ Ajouter</n-button>
          </template>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <n-tag
              v-for="cat in categories"
              :key="cat.id"
              :color="cat.color ? { color: cat.color + '22', borderColor: cat.color, textColor: cat.color } : undefined"
              :closable="!cat.is_system"
              @close="deleteCategory(cat.id)"
              @click="!cat.is_system && openCategoryModal(cat)"
              style="cursor: pointer; user-select: none;"
            >
              <span v-if="cat.icon" style="margin-right: 4px;">{{ cat.icon }}</span>
              {{ cat.name }}
              <n-tag v-if="cat.is_system" size="tiny" style="margin-left: 4px; opacity: 0.6;">sys</n-tag>
            </n-tag>
          </div>
        </n-card>

        <!-- Règles de catégorisation -->
        <n-card embedded bordered style="margin-top: 16px;" title="Règles de catégorisation automatique">
          <template #header-extra>
            <n-space>
              <n-button size="small" :loading="applyLoading" @click="applyRules(false)">
                ▶️ Appliquer aux non catégorisées
              </n-button>
              <n-button size="small" secondary :loading="applyLoading" @click="applyRules(true)">
                🔄 Tout recatégoriser
              </n-button>
              <n-button size="small" type="primary" @click="openRuleModal()">+ Ajouter une règle</n-button>
            </n-space>
          </template>

          <n-alert type="info" :bordered="false" style="margin-bottom: 12px;">
            Les règles s'appliquent par <b>priorité décroissante</b> — la première qui correspond l'emporte.
          </n-alert>

          <n-data-table
            :columns="ruleColumns"
            :data="rules"
            :bordered="false"
            size="small"
          />
        </n-card>
      </n-tab-pane>

      <!-- Modal catégorie -->
      <n-modal v-model:show="showCategoryModal" preset="card" title="Catégorie" style="width: 400px;">
        <n-form :model="categoryForm" label-placement="top">
          <n-form-item label="Nom">
            <n-input v-model:value="categoryForm.name" placeholder="Alimentation" />
          </n-form-item>
          <n-form-item label="Icône (emoji)">
            <n-input v-model:value="categoryForm.icon" placeholder="🛒" maxlength="4" />
          </n-form-item>
          <n-form-item label="Couleur">
            <n-color-picker v-model:value="categoryForm.color" :show-alpha="false" />
          </n-form-item>
          <n-form-item label="Type">
            <n-radio-group v-model:value="categoryForm.is_income">
              <n-radio :value="false">Dépense</n-radio>
              <n-radio :value="true">Revenu</n-radio>
            </n-radio-group>
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showCategoryModal = false">Annuler</n-button>
            <n-button type="primary" :loading="catSaveLoading" @click="saveCategory">
              {{ editingCategory ? 'Modifier' : 'Créer' }}
            </n-button>
          </n-space>
        </template>
      </n-modal>

      <!-- Modal règle -->
      <n-modal v-model:show="showRuleModal" preset="card" title="Règle de catégorisation" style="width: 480px;">
        <n-form :model="ruleForm" label-placement="top">
          <n-form-item label="Motif (pattern)">
            <n-input v-model:value="ruleForm.pattern" placeholder="FREE MOBILE, AMAZON, ^VIR.*SALAIRE" />
          </n-form-item>
          <n-form-item label="Type de correspondance">
            <n-select v-model:value="ruleForm.match_type" :options="matchTypeOptions" />
          </n-form-item>
          <n-form-item label="Catégorie cible">
            <n-select
              v-model:value="ruleForm.category_id"
              :options="categorySelectOptions"
              filterable
              placeholder="Choisir une catégorie"
            />
          </n-form-item>
          <n-form-item label="Priorité (plus grand = plus prioritaire)">
            <n-input-number v-model:value="ruleForm.priority" :min="0" :max="999" style="width: 100%;" />
          </n-form-item>
          <n-form-item label="Active">
            <n-switch v-model:value="ruleForm.is_active" />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showRuleModal = false">Annuler</n-button>
            <n-button type="primary" :loading="ruleSaveLoading" @click="saveRule">
              {{ editingRule ? 'Modifier' : 'Créer' }}
            </n-button>
          </n-space>
        </template>
      </n-modal>

    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue'
import { useMessage, NButton, NSpace, NTag, NSwitch } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { settingsApi } from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'
import { accountsApi } from '@/api/accounts'
import type { CARegion } from '@/api/accounts'
import api from '@/api/client'
import { categoriesApi, categoryRulesApi } from '@/api/categories'
import type { Category, CategoryRule } from '@/api/categories'

const settingsStore = useSettingsStore()
const message = useMessage()

// --- Crédit Agricole ---
const caForm = ref({ region: '', login: '', password: '' })
const caLoading = ref(false)
const testLoading = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const scrapingEnabled = ref(true)
const scrapingTime = ref<number | null>(null)
const syncLoading = ref(false)
const syncStatus = ref<string>('')
const regions = ref<CARegion[]>([])

const regionOptions = computed(() =>
  regions.value.map((r) => ({ label: r.name, value: r.id }))
)

async function saveCASettings() {
  caLoading.value = true
  try {
    await settingsStore.setBatch({
      'ca.region': caForm.value.region,
      'ca.login': caForm.value.login,
      ...(caForm.value.password ? { 'ca.password': caForm.value.password } : {}),
    })
    message.success('Paramètres CA enregistrés')
    caForm.value.password = '' // Effacer le mot de passe du formulaire
  } catch {
    message.error('Erreur lors de la sauvegarde')
  } finally {
    caLoading.value = false
  }
}

async function testCAConnection() {
  if (!caForm.value.region || !caForm.value.login || !caForm.value.password) {
    message.warning('Remplissez la région, l\'identifiant et le code avant de tester')
    return
  }
  testLoading.value = true
  testResult.value = null
  try {
    const { data } = await settingsApi.testConnection(caForm.value.region, caForm.value.login, caForm.value.password)
    testResult.value = data
  } catch (e: any) {
    testResult.value = { success: false, message: e?.response?.data?.detail ?? 'Erreur de connexion' }
  } finally {
    testLoading.value = false
  }
}

async function saveScraping() {
  const hour = scrapingTime.value ? new Date(scrapingTime.value).getHours() : 6
  const minute = scrapingTime.value ? new Date(scrapingTime.value).getMinutes() : 0
  await settingsStore.setBatch({
    'scraping.enabled': scrapingEnabled.value,
    'scraping.schedule_hour': String(hour),
    'scraping.schedule_minute': String(minute),
  })
}

async function triggerSyncNow() {
  syncLoading.value = true
  try {
    await settingsApi.triggerScraping()
    message.success('Synchronisation lancée en arrière-plan')
    pollSyncStatus()
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur')
  } finally {
    syncLoading.value = false
  }
}

async function pollSyncStatus() {
  const { data } = await settingsApi.getScraperStatus()
  syncStatus.value = data.status
  if (data.status === 'running') setTimeout(pollSyncStatus, 3000)
}

// --- IA ---
const aiForm = ref({ provider: 'groq', model: '', groqKey: '', mistralKey: '', ollamaUrl: '', autoCategorize: true })
const aiLoading = ref(false)
const defaultModelPlaceholder = computed(() => {
  if (aiForm.value.provider === 'groq') return 'llama-3.3-70b-versatile'
  if (aiForm.value.provider === 'mistral') return 'mistral-large-latest'
  return 'mistral-nemo:12b'
})

async function saveAISettings() {
  aiLoading.value = true
  try {
    await settingsStore.setBatch({
      'ai.provider': aiForm.value.provider,
      'ai.model': aiForm.value.model || defaultModelPlaceholder.value,
      'ai.auto_categorize': aiForm.value.autoCategorize,
      ...(aiForm.value.groqKey ? { 'ai.groq_api_key': aiForm.value.groqKey } : {}),
      ...(aiForm.value.mistralKey ? { 'ai.mistral_api_key': aiForm.value.mistralKey } : {}),
      ...(aiForm.value.ollamaUrl ? { 'ollama_base_url': aiForm.value.ollamaUrl } : {}),
    })
    message.success('Paramètres IA enregistrés')
    aiForm.value.groqKey = ''
    aiForm.value.mistralKey = ''
  } catch {
    message.error('Erreur lors de la sauvegarde')
  } finally {
    aiLoading.value = false
  }
}

// --- Notifications ---
const notifForm = ref({
  enabled: false, url: '', topic: 'bankassistant',
  budgetAlert: true, largeTransactionThreshold: 500,
  dailyReport: false, dailyReportTime: null as number | null,
})
const notifLoading = ref(false)

async function saveNotifSettings() {
  notifLoading.value = true
  try {
    const hour = notifForm.value.dailyReportTime
      ? new Date(notifForm.value.dailyReportTime).getHours() : 8
    await settingsStore.setBatch({
      'notifications.enabled': notifForm.value.enabled,
      'notifications.budget_alert': notifForm.value.budgetAlert,
      'notifications.large_transaction_threshold': String(notifForm.value.largeTransactionThreshold),
      'notifications.daily_report': notifForm.value.dailyReport,
      'notifications.daily_report_hour': String(hour),
    })
    message.success('Notifications enregistrées')
  } catch {
    message.error('Erreur lors de la sauvegarde')
  } finally {
    notifLoading.value = false
  }
}

async function sendTestNotification() {
  try {
    await api.post('/notifications/test')
    message.success('Notification de test envoyée !')
  } catch {
    message.error('Échec — vérifiez l\'URL ntfy et le topic')
  }
}

// --- Catégories ---
const categories = ref<Category[]>([])
const showCategoryModal = ref(false)
const catSaveLoading = ref(false)
const editingCategory = ref<Category | null>(null)
const categoryForm = ref({ name: '', icon: '', color: '#18a058', is_income: false })

const categorySelectOptions = computed(() =>
  categories.value.map(c => ({ label: `${c.icon ?? ''} ${c.name}`.trim(), value: c.id }))
)

function openCategoryModal(cat?: Category) {
  editingCategory.value = cat ?? null
  categoryForm.value = {
    name: cat?.name ?? '',
    icon: cat?.icon ?? '',
    color: cat?.color ?? '#18a058',
    is_income: cat?.is_income ?? false,
  }
  showCategoryModal.value = true
}

async function saveCategory() {
  if (!categoryForm.value.name.trim()) { message.warning('Nom requis'); return }
  catSaveLoading.value = true
  try {
    const payload = {
      name: categoryForm.value.name,
      icon: categoryForm.value.icon || null,
      color: categoryForm.value.color || null,
      is_income: categoryForm.value.is_income,
    }
    if (editingCategory.value) {
      await categoriesApi.update(editingCategory.value.id, payload)
      message.success('Catégorie modifiée')
    } else {
      await categoriesApi.create(payload)
      message.success('Catégorie créée')
    }
    showCategoryModal.value = false
    categories.value = (await categoriesApi.list()).data
  } catch {
    message.error('Erreur lors de la sauvegarde')
  } finally {
    catSaveLoading.value = false
  }
}

async function deleteCategory(id: string) {
  try {
    await categoriesApi.delete(id)
    categories.value = categories.value.filter(c => c.id !== id)
    message.success('Catégorie supprimée')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur')
  }
}

// --- Règles ---
const rules = ref<CategoryRule[]>([])
const showRuleModal = ref(false)
const ruleSaveLoading = ref(false)
const applyLoading = ref(false)
const editingRule = ref<CategoryRule | null>(null)
const ruleForm = ref({ pattern: '', match_type: 'contains', category_id: '', priority: 0, is_active: true })

const matchTypeOptions = [
  { label: 'Contient', value: 'contains' },
  { label: 'Commence par', value: 'starts_with' },
  { label: 'Finit par', value: 'ends_with' },
  { label: 'Expression régulière', value: 'regex' },
]

function openRuleModal(rule?: CategoryRule) {
  editingRule.value = rule ?? null
  ruleForm.value = {
    pattern: rule?.pattern ?? '',
    match_type: rule?.match_type ?? 'contains',
    category_id: rule?.category_id ?? '',
    priority: rule?.priority ?? 0,
    is_active: rule?.is_active ?? true,
  }
  showRuleModal.value = true
}

async function saveRule() {
  if (!ruleForm.value.pattern.trim()) { message.warning('Motif requis'); return }
  if (!ruleForm.value.category_id) { message.warning('Catégorie requise'); return }
  ruleSaveLoading.value = true
  try {
    if (editingRule.value) {
      await categoryRulesApi.update(editingRule.value.id, ruleForm.value)
      message.success('Règle modifiée')
    } else {
      await categoryRulesApi.create(ruleForm.value)
      message.success('Règle créée')
    }
    showRuleModal.value = false
    rules.value = (await categoryRulesApi.list()).data
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur')
  } finally {
    ruleSaveLoading.value = false
  }
}

async function deleteRule(id: string) {
  try {
    await categoryRulesApi.delete(id)
    rules.value = rules.value.filter(r => r.id !== id)
    message.success('Règle supprimée')
  } catch {
    message.error('Erreur lors de la suppression')
  }
}

async function applyRules(allTransactions: boolean) {
  applyLoading.value = true
  try {
    const { data } = await categoryRulesApi.apply(allTransactions)
    message.success(data.message)
  } catch {
    message.error('Erreur lors de l\'application des règles')
  } finally {
    applyLoading.value = false
  }
}

const ruleColumns: DataTableColumns<CategoryRule> = [
  { title: 'Motif', key: 'pattern', ellipsis: { tooltip: true } },
  {
    title: 'Type',
    key: 'match_type',
    width: 140,
    render: (row) => {
      const labels: Record<string, string> = {
        contains: 'Contient', starts_with: 'Commence par',
        ends_with: 'Finit par', regex: 'Regex',
      }
      return labels[row.match_type] ?? row.match_type
    },
  },
  { title: 'Catégorie', key: 'category_name', width: 160 },
  { title: 'Priorité', key: 'priority', width: 80 },
  {
    title: 'Active',
    key: 'is_active',
    width: 80,
    render: (row) => h(NSwitch, {
      value: row.is_active,
      size: 'small',
      onUpdateValue: async (val: boolean) => {
        await categoryRulesApi.update(row.id, { ...row, is_active: val })
        const r = rules.value.find(r => r.id === row.id)
        if (r) r.is_active = val
      },
    }),
  },
  {
    title: '',
    key: 'actions',
    width: 100,
    render: (row) => h(NSpace, { size: 'small' }, {
      default: () => [
        h(NButton, { size: 'tiny', onClick: () => openRuleModal(row) }, { default: () => '✏️' }),
        h(NButton, { size: 'tiny', type: 'error', onClick: () => deleteRule(row.id) }, { default: () => '🗑️' }),
      ],
    }),
  },
]

// --- Init ---
onMounted(async () => {
  await settingsStore.fetchSettings()
  regions.value = (await accountsApi.listRegions()).data

  // Pré-remplir les formulaires
  caForm.value.region = String(settingsStore.get('ca.region', ''))
  scrapingEnabled.value = settingsStore.get('scraping.enabled', 'true') === 'true'

  aiForm.value.provider = String(settingsStore.get('ai.provider', 'groq'))
  aiForm.value.model = String(settingsStore.get('ai.model', ''))
  aiForm.value.autoCategorize = settingsStore.get('ai.auto_categorize', 'true') === 'true'

  notifForm.value.enabled = settingsStore.get('notifications.enabled', 'false') === 'true'
  notifForm.value.budgetAlert = settingsStore.get('notifications.budget_alert', 'true') === 'true'
  notifForm.value.largeTransactionThreshold = Number(settingsStore.get('notifications.large_transaction_threshold', '500'))
  notifForm.value.dailyReport = settingsStore.get('notifications.daily_report', 'false') === 'true'

  // Catégories & règles
  categories.value = (await categoriesApi.list()).data
  rules.value = (await categoryRulesApi.list()).data

  // Statut scraper
  pollSyncStatus()
})
</script>
