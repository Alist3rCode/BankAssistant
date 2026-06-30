<template>
  <n-config-provider :theme="theme" :theme-overrides="themeOverrides" :locale="frFR" :date-locale="dateFrFR">
    <n-loading-bar-provider>
      <n-notification-provider placement="top-right">
        <n-message-provider placement="top">
          <router-view />
        </n-message-provider>
      </n-notification-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { darkTheme, frFR, dateFrFR, type GlobalThemeOverrides } from 'naive-ui'
import { useOsTheme } from '@vueuse/core'

const osTheme = useOsTheme()
const theme = computed(() => (osTheme.value === 'dark' ? darkTheme : null))

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#18a058',
    primaryColorHover: '#36ad6a',
    primaryColorPressed: '#0c7a43',
    primaryColorSuppl: '#36ad6a',
  },
}
</script>
