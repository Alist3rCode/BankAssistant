<template>
  <div>
    <!-- 2FA -->
    <n-card embedded bordered style="margin-bottom: 16px;" title="Authentification à deux facteurs (2FA)">
      <n-space vertical :size="16">
        <n-space align="center">
          <n-tag :type="user?.totp_enabled ? 'success' : 'warning'">
            {{ user?.totp_enabled ? '✅ 2FA activé' : '⚠️ 2FA désactivé' }}
          </n-tag>
          <n-text depth="3">
            {{ user?.totp_enabled
              ? 'Votre compte est protégé par le 2FA (Google Authenticator, Authy…)'
              : 'Activez le 2FA pour renforcer la sécurité de votre compte' }}
          </n-text>
        </n-space>

        <!-- Setup 2FA -->
        <div v-if="!user?.totp_enabled">
          <n-button type="primary" :loading="setupLoading" @click="setup2FA">
            🔐 Activer le 2FA
          </n-button>

          <div v-if="qrCode" style="margin-top: 20px;">
            <n-alert type="info" :bordered="false" style="margin-bottom: 16px;">
              Scannez ce QR code avec Google Authenticator ou Authy, puis entrez le code généré pour confirmer.
            </n-alert>
            <div style="display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-start;">
              <img :src="`data:image/png;base64,${qrCode}`" alt="QR Code 2FA" style="width: 180px; border-radius: 8px;" />
              <div>
                <n-text depth="3" style="font-size: 12px;">Clé manuelle :</n-text><br />
                <n-code :code="totpSecret" language="text" style="font-size: 13px;" />
                <n-form style="margin-top: 16px;">
                  <n-form-item label="Code de confirmation (6 chiffres)" :show-feedback="false">
                    <n-input
                      v-model:value="confirmCode"
                      placeholder="123456"
                      maxlength="6"
                      style="width: 140px; font-size: 18px; letter-spacing: 4px;"
                      @keyup.enter="confirm2FA"
                    />
                  </n-form-item>
                  <n-button type="primary" :loading="confirmLoading" @click="confirm2FA">
                    ✅ Confirmer
                  </n-button>
                </n-form>
              </div>
            </div>
          </div>
        </div>

        <!-- Désactiver 2FA -->
        <div v-else>
          <n-popconfirm @positive-click="disable2FA">
            <template #trigger>
              <n-button type="error" ghost>
                🔓 Désactiver le 2FA
              </n-button>
            </template>
            Confirmer la désactivation du 2FA ? Votre compte sera moins sécurisé.
          </n-popconfirm>
        </div>
      </n-space>
    </n-card>

    <!-- Changer mot de passe -->
    <n-card embedded bordered style="margin-bottom: 16px;" title="Changer le mot de passe">
      <n-form label-placement="top" style="max-width: 400px;">
        <n-form-item label="Nouveau mot de passe">
          <n-input v-model:value="newPassword" type="password" show-password-on="click" placeholder="••••••••" />
        </n-form-item>
        <n-form-item label="Confirmer le mot de passe">
          <n-input v-model:value="confirmPassword" type="password" show-password-on="click" placeholder="••••••••" />
        </n-form-item>
        <n-button type="primary" :loading="pwdLoading" :disabled="!newPassword || newPassword !== confirmPassword" @click="changePassword">
          💾 Changer le mot de passe
        </n-button>
        <n-text v-if="newPassword && confirmPassword && newPassword !== confirmPassword" type="error" style="display: block; margin-top: 8px; font-size: 12px;">
          Les mots de passe ne correspondent pas
        </n-text>
      </n-form>
    </n-card>

    <!-- Journal d'audit -->
    <n-card embedded bordered title="Journal d'activité">
      <n-data-table
        :columns="auditColumns"
        :data="auditLogs"
        :loading="auditLoading"
        :pagination="{ pageSize: 20 }"
        size="small"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import type { DataTableColumns } from 'naive-ui'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const auth = useAuthStore()
const message = useMessage()
const user = computed(() => auth.user)

// --- 2FA ---
const setupLoading = ref(false)
const confirmLoading = ref(false)
const qrCode = ref('')
const totpSecret = ref('')
const confirmCode = ref('')

async function setup2FA() {
  setupLoading.value = true
  try {
    const { data } = await authApi.setupTotp()
    qrCode.value = data.qr_code_base64
    totpSecret.value = data.secret
  } catch {
    message.error('Erreur lors de la génération du 2FA')
  } finally {
    setupLoading.value = false
  }
}

async function confirm2FA() {
  if (confirmCode.value.length !== 6) return
  confirmLoading.value = true
  try {
    await authApi.confirmTotp(confirmCode.value)
    message.success('2FA activé avec succès !')
    await auth.fetchMe()
    qrCode.value = ''
    confirmCode.value = ''
  } catch {
    message.error('Code invalide. Réessayez.')
    confirmCode.value = ''
  } finally {
    confirmLoading.value = false
  }
}

async function disable2FA() {
  try {
    await authApi.disableTotp()
    message.success('2FA désactivé')
    await auth.fetchMe()
  } catch {
    message.error('Erreur lors de la désactivation')
  }
}

// --- Mot de passe ---
const newPassword = ref('')
const confirmPassword = ref('')
const pwdLoading = ref(false)

async function changePassword() {
  if (newPassword.value !== confirmPassword.value) return
  pwdLoading.value = true
  try {
    await api.put('/auth/password', { password: newPassword.value })
    message.success('Mot de passe changé avec succès')
    newPassword.value = ''
    confirmPassword.value = ''
  } catch {
    message.error('Erreur lors du changement de mot de passe')
  } finally {
    pwdLoading.value = false
  }
}

// --- Journal d'audit ---
const auditLogs = ref<any[]>([])
const auditLoading = ref(false)

const auditColumns: DataTableColumns = [
  {
    title: 'Date',
    key: 'created_at',
    width: 160,
    render: (row: any) => format(new Date(row.created_at), 'dd/MM/yyyy HH:mm', { locale: fr }),
  },
  { title: 'Action', key: 'action', width: 160 },
  { title: 'IP', key: 'ip_address', width: 130 },
  { title: 'Détails', key: 'details', ellipsis: { tooltip: true } },
]

onMounted(async () => {
  auditLoading.value = true
  try {
    const { data } = await api.get('/audit-logs/')
    auditLogs.value = data
  } catch {
    // silencieux si pas encore d'endpoint
  } finally {
    auditLoading.value = false
  }
})
</script>
