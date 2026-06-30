<template>
  <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); padding: 20px;">
    <n-card style="width: 100%; max-width: 420px;" :bordered="false">
      <!-- En-tête -->
      <div style="text-align: center; margin-bottom: 32px;">
        <div style="font-size: 40px; margin-bottom: 8px;">💳</div>
        <n-h2 style="margin: 0; color: #18a058;">BankAssistant</h2>
        <n-text depth="3" style="font-size: 14px;">Assistant bancaire IA — Crédit Agricole</n-text>
      </div>

      <!-- Étape 1 : Email + mot de passe -->
      <n-form v-if="step === 'credentials'" @submit.prevent="handleLogin">
        <n-form-item label="Email" :show-feedback="false" style="margin-bottom: 16px;">
          <n-input
            v-model:value="email"
            type="email"
            placeholder="votre@email.fr"
            size="large"
            :disabled="loading"
            @keyup.enter="handleLogin"
          />
        </n-form-item>
        <n-form-item label="Mot de passe" :show-feedback="false" style="margin-bottom: 24px;">
          <n-input
            v-model:value="password"
            type="password"
            placeholder="••••••••"
            show-password-on="click"
            size="large"
            :disabled="loading"
            @keyup.enter="handleLogin"
          />
        </n-form-item>

        <n-alert v-if="errorMsg" type="error" :bordered="false" style="margin-bottom: 16px;">
          {{ errorMsg }}
        </n-alert>

        <n-button type="primary" size="large" block :loading="loading" @click="handleLogin">
          Se connecter
        </n-button>
      </n-form>

      <!-- Étape 2 : Code TOTP -->
      <div v-else-if="step === 'totp'">
        <n-alert type="info" :bordered="false" style="margin-bottom: 20px;">
          Entrez le code à 6 chiffres de votre application d'authentification (Google Authenticator, Authy…)
        </n-alert>

        <n-form @submit.prevent="handleTotp">
          <n-form-item label="Code TOTP" :show-feedback="false" style="margin-bottom: 24px;">
            <n-input
              ref="totpInputRef"
              v-model:value="totpCode"
              placeholder="123456"
              size="large"
              maxlength="6"
              :disabled="loading"
              style="font-size: 24px; letter-spacing: 8px; text-align: center;"
              @keyup.enter="handleTotp"
            />
          </n-form-item>

          <n-alert v-if="errorMsg" type="error" :bordered="false" style="margin-bottom: 16px;">
            {{ errorMsg }}
          </n-alert>

          <n-space vertical>
            <n-button type="primary" size="large" block :loading="loading" @click="handleTotp">
              Valider
            </n-button>
            <n-button size="large" block :disabled="loading" @click="step = 'credentials'">
              Retour
            </n-button>
          </n-space>
        </n-form>
      </div>

      <!-- Première connexion : créer un compte -->
      <div v-else-if="step === 'register'">
        <n-alert type="warning" :bordered="false" style="margin-bottom: 20px;">
          Aucun compte trouvé. Créez votre compte administrateur.
        </n-alert>
        <n-form @submit.prevent="handleRegister">
          <n-form-item label="Email" :show-feedback="false" style="margin-bottom: 16px;">
            <n-input v-model:value="email" type="email" placeholder="votre@email.fr" size="large" />
          </n-form-item>
          <n-form-item label="Mot de passe" :show-feedback="false" style="margin-bottom: 24px;">
            <n-input v-model:value="password" type="password" placeholder="••••••••" show-password-on="click" size="large" />
          </n-form-item>
          <n-alert v-if="errorMsg" type="error" :bordered="false" style="margin-bottom: 16px;">{{ errorMsg }}</n-alert>
          <n-button type="primary" size="large" block :loading="loading" @click="handleRegister">
            Créer mon compte
          </n-button>
        </n-form>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const step = ref<'credentials' | 'totp' | 'register'>('credentials')
const email = ref('')
const password = ref('')
const totpCode = ref('')
const pendingUserId = ref('')
const loading = ref(false)
const errorMsg = ref('')
const totpInputRef = ref()

async function handleLogin() {
  if (!email.value || !password.value) return
  errorMsg.value = ''
  loading.value = true
  try {
    const result = await auth.login(email.value, password.value)
    if (result.requires_totp) {
      pendingUserId.value = result.user_id
      step.value = 'totp'
      await nextTick()
      totpInputRef.value?.focus()
    } else {
      redirect()
    }
  } catch (e: any) {
    const status = e?.response?.status
    if (status === 423) {
      errorMsg.value = 'Compte temporairement verrouillé. Réessayez plus tard.'
    } else if (status === 401) {
      errorMsg.value = 'Email ou mot de passe incorrect.'
    } else if (status === 422 || status === 404) {
      step.value = 'register'
    } else {
      errorMsg.value = e?.response?.data?.detail ?? 'Erreur de connexion'
    }
  } finally {
    loading.value = false
  }
}

async function handleTotp() {
  if (totpCode.value.length !== 6) return
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.loginWithTotp(pendingUserId.value, totpCode.value, '')
    redirect()
  } catch {
    errorMsg.value = 'Code TOTP invalide ou expiré.'
    totpCode.value = ''
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!email.value || !password.value) return
  errorMsg.value = ''
  loading.value = true
  try {
    await authApi.register(email.value, password.value)
    await auth.login(email.value, password.value)
    redirect()
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Erreur lors de la création du compte'
  } finally {
    loading.value = false
  }
}

function redirect() {
  const target = route.query.redirect as string | undefined
  router.push(target ?? '/dashboard')
}
</script>
