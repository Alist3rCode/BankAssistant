<template>
  <div style="display: flex; flex-direction: column; height: 100%;">
    <!-- Logo -->
    <div style="padding: 16px; border-bottom: 1px solid var(--n-border-color); text-align: center;">
      <span v-if="!collapsed" style="font-size: 16px; font-weight: 700; color: #18a058;">
        💳 BankAssistant
      </span>
      <span v-else style="font-size: 20px;">💳</span>
    </div>

    <!-- Menu de navigation -->
    <n-menu
      :collapsed="collapsed"
      :collapsed-width="64"
      :collapsed-icon-size="20"
      :options="menuOptions"
      :value="activeKey"
      @update:value="navigate"
      style="flex: 1; padding-top: 8px;"
    />

    <!-- Version en bas -->
    <div v-if="!collapsed" style="padding: 12px 16px; font-size: 11px; color: var(--n-text-color-disabled); border-top: 1px solid var(--n-border-color);">
      BankAssistant v1.0
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MenuOption } from 'naive-ui'

const props = defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const router = useRouter()

const activeKey = computed(() => route.name as string)

// Icônes SVG inline
function icon(d: string) {
  return () => h('svg', { width: '18', height: '18', viewBox: '0 0 24 24', fill: 'currentColor' }, [h('path', { d })])
}

const menuOptions: MenuOption[] = [
  {
    label: 'Tableau de bord',
    key: 'dashboard',
    icon: icon('M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z'),
  },
  {
    label: 'Transactions',
    key: 'transactions',
    icon: icon('M20 4H4c-1.11 0-1.99.89-1.99 2L2 18c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z'),
  },
  {
    label: 'Budgets',
    key: 'budgets',
    icon: icon('M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z'),
  },
  {
    label: 'Assistant IA',
    key: 'chat',
    icon: icon('M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z'),
  },
  { type: 'divider', key: 'div1' },
  {
    label: 'Paramètres',
    key: 'settings',
    icon: icon('M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.477.477 0 0 0-.59.22L2.74 8.87a.47.47 0 0 0 .12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.47.47 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'),
  },
  {
    label: 'Sécurité',
    key: 'security',
    icon: icon('M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z'),
  },
]

function navigate(key: string) {
  router.push({ name: key })
  emit('navigate')
}
</script>
