<template>
  <n-layout has-sider style="height: 100vh;">
    <!-- Sidebar desktop -->
    <n-layout-sider
      v-if="!isMobile"
      :collapsed="collapsed"
      :collapsed-width="64"
      :width="220"
      collapse-mode="width"
      show-trigger="bar"
      bordered
      @update:collapsed="collapsed = $event"
    >
      <AppSidebar :collapsed="collapsed" />
    </n-layout-sider>

    <!-- Contenu principal -->
    <n-layout>
      <!-- Topbar -->
      <n-layout-header bordered style="height: 56px; display: flex; align-items: center; padding: 0 16px; gap: 12px;">
        <!-- Burger mobile -->
        <n-button v-if="isMobile" quaternary circle @click="showMobileDrawer = true">
          <template #icon><n-icon :component="MenuIcon" /></template>
        </n-button>

        <span style="font-weight: 700; font-size: 18px; color: var(--n-text-color);">
          {{ pageTitle }}
        </span>

        <div style="flex: 1" />

        <!-- Badge sync -->
        <n-tooltip>
          <template #trigger>
            <n-button quaternary circle :loading="syncLoading" @click="triggerSync">
              <template #icon><n-icon :component="RefreshIcon" /></template>
            </n-button>
          </template>
          Synchroniser avec Crédit Agricole
        </n-tooltip>

        <!-- Avatar utilisateur -->
        <n-dropdown :options="userMenuOptions" @select="handleUserMenu">
          <n-avatar round size="small" style="cursor: pointer; background-color: #18a058; color: white;">
            {{ userInitial }}
          </n-avatar>
        </n-dropdown>
      </n-layout-header>

      <!-- Contenu de la page -->
      <n-layout-content style="overflow: auto; height: calc(100vh - 56px);">
        <div style="padding: 20px; max-width: 1280px; margin: 0 auto;">
          <router-view />
        </div>
      </n-layout-content>
    </n-layout>

    <!-- Drawer mobile -->
    <n-drawer v-model:show="showMobileDrawer" :width="240" placement="left">
      <n-drawer-content title="BankAssistant" :native-scrollbar="false">
        <AppSidebar :collapsed="false" @navigate="showMobileDrawer = false" />
      </n-drawer-content>
    </n-drawer>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import AppSidebar from './AppSidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/settings'

// Icônes inline simples (pas de dépendance externe)
const MenuIcon = { render: () => h('svg', { viewBox: '0 0 24 24', fill: 'currentColor' }, [
  h('path', { d: 'M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z' })
]) }
const RefreshIcon = { render: () => h('svg', { viewBox: '0 0 24 24', fill: 'currentColor' }, [
  h('path', { d: 'M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z' })
]) }

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const message = useMessage()
const breakpoints = useBreakpoints(breakpointsTailwind)
const isMobile = breakpoints.smaller('lg')

const collapsed = ref(false)
const showMobileDrawer = ref(false)
const syncLoading = ref(false)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    dashboard: 'Tableau de bord',
    transactions: 'Transactions',
    budgets: 'Budgets',
    chat: 'Assistant IA',
    settings: 'Paramètres',
    security: 'Sécurité',
  }
  return titles[route.name as string] ?? 'BankAssistant'
})

const userInitial = computed(() => {
  const email = auth.user?.email ?? ''
  return email.charAt(0).toUpperCase() || 'U'
})

const userMenuOptions = [
  { label: 'Mon compte', key: 'account', disabled: true },
  { label: auth.user?.email ?? '', key: 'email', disabled: true },
  { type: 'divider', key: 'd1' },
  { label: 'Sécurité & 2FA', key: 'security' },
  { type: 'divider', key: 'd2' },
  { label: 'Se déconnecter', key: 'logout' },
]

function handleUserMenu(key: string) {
  if (key === 'logout') {
    auth.logout()
    router.push('/login')
  } else if (key === 'security') {
    router.push('/security')
  }
}

async function triggerSync() {
  syncLoading.value = true
  try {
    await settingsApi.triggerScraping()
    message.success('Synchronisation lancée en arrière-plan')
  } catch (e: any) {
    message.error(e?.response?.data?.detail ?? 'Erreur de synchronisation')
  } finally {
    syncLoading.value = false
  }
}
</script>
