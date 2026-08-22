<script setup>
import { onMounted, ref } from "vue";
import { api, clearToken, getToken, setToken } from "./api";
import LoginPage from "./components/LoginPage.vue";
import Workspace from "./components/Workspace.vue";

const user = ref(null);
const ready = ref(false);

async function restoreSession() {
  if (!getToken()) {
    ready.value = true;
    return;
  }
  try {
    user.value = await api.me();
  } catch {
    clearToken();
    user.value = null;
  } finally {
    ready.value = true;
  }
}

async function handleLogin(payload) {
  setToken(payload.token);
  user.value = payload.user;
}

async function handleLogout() {
  try {
    await api.logout();
  } catch {
    // Token may already be invalid.
  }
  clearToken();
  user.value = null;
}

onMounted(restoreSession);
</script>

<template>
  <LoginPage v-if="ready && !user" @logged-in="handleLogin" />
  <Workspace
    v-else-if="ready && user"
    :user="user"
    @logout="handleLogout"
  />
</template>
