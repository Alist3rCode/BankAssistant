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
        <n-card embedded bordered style="margin-top: 16px;" title="Règles de catégorisation automatique">
          <n-alert type="info" :bordered="false" style="margin-bottom: 16px;">
            Ces règles sont appliquées automatiquement lors du scraping. Elles s'appliquent en priorité croissante.
          </n-alert>
          <n-empty description="La gestion complète des catégories et règles sera disponible dans la prochaine version." />
        </n-card>
      </n-tab-pane>

    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { settingsApi } from '@/api/settings'
import { useSettingsStore } from '@/stores/settings'
import { accountsApi } from '@/api/accounts'
import type { CARegion } from '@/api/accounts'
import api from '@/api/client'

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

  // Statut scraper
  pollSyncStatus()
})
</script>
