<template>
  <div class="container">
    <header>
      <h1>TaskFlow</h1>
      <p>Exemplo simples – Flask API + Vue 3</p>
    </header>

    <section class="card">
      <h2>Status da API</h2>
      <p v-if="health">{{ health.message }}</p>
      <p v-else class="loading">Carregando...</p>
    </section>

    <section class="card">
      <h2>Projetos</h2>
      <ul v-if="projects.length">
        <li v-for="project in projects" :key="project.id">
          <strong>{{ project.name }}</strong>
          <span class="badge">{{ project.status }}</span>
        </li>
      </ul>
      <p v-else class="loading">Carregando projetos...</p>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from './services/api'

const health = ref(null)
const projects = ref([])

onMounted(async () => {
  try {
    const healthRes = await api.get('/health')
    health.value = healthRes.data

    const projectsRes = await api.get('/projects')
    projects.value = projectsRes.data
  } catch (error) {
    console.error('Erro ao comunicar com a API:', error)
    health.value = { message: 'Não foi possível conectar à API' }
  }
})
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #f4f6f8;
  color: #222;
  line-height: 1.5;
}

.container {
  max-width: 720px;
  margin: 40px auto;
  padding: 0 20px;
}

header {
  margin-bottom: 32px;
}

header h1 {
  font-size: 2rem;
  margin-bottom: 4px;
}

header p {
  color: #666;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.card h2 {
  font-size: 1.2rem;
  margin-bottom: 16px;
}

ul {
  list-style: none;
}

li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

li:last-child {
  border-bottom: none;
}

.badge {
  background: #e8f0fe;
  color: #1a73e8;
  font-size: 0.8rem;
  padding: 4px 10px;
  border-radius: 20px;
  text-transform: capitalize;
}

.loading {
  color: #888;
}
</style>