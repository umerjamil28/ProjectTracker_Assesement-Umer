<script setup>
import { ref } from "vue";
import { api } from "../api";

const emit = defineEmits(["logged-in"]);

const username = ref("alice");
const password = ref("DemoPass123!");
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const payload = await api.login(username.value, password.value);
    emit("logged-in", payload);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login">
    <section class="panel">
      <p class="eyebrow">Project Tracker</p>
      <h1>Atlas</h1>
      <p class="lede">
        Sign in to see projects, open work, and live task updates for your
        organizations.
      </p>

      <form @submit.prevent="submit">
        <label>
          Username
          <input v-model.trim="username" autocomplete="username" />
        </label>
        <label>
          Password
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
          />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">
          {{ loading ? "Signing in…" : "Enter workspace" }}
        </button>
      </form>

      <p class="hint">
        Try <strong>alice</strong> (admin + member), <strong>bob</strong>
        (member), or <strong>carol</strong> (viewer). Password
        <code>DemoPass123!</code>
      </p>
    </section>
  </main>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 16px;
}

.panel {
  width: min(440px, 100%);
  padding: 36px 32px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 28px;
  box-shadow: var(--shadow);
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 0.82rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  font-size: 3rem;
}

.lede,
.hint {
  color: var(--muted);
  line-height: 1.5;
}

form {
  display: grid;
  gap: 14px;
  margin: 28px 0 18px;
}

label {
  display: grid;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--muted);
}

input {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
}

button {
  margin-top: 6px;
  padding: 13px 16px;
  border: 0;
  border-radius: 12px;
  background: var(--accent);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

button:hover {
  background: var(--accent-dark);
}

.error {
  margin: 0;
  color: #9f1239;
}

.hint {
  font-size: 0.88rem;
}

code {
  font-size: 0.84em;
}
</style>
