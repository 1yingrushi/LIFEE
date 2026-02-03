<script setup>
import { onMounted, ref, computed } from 'vue'

const API_BASE = 'http://127.0.0.1:8000'

// ----- View state -----
const view = ref('home') // 'home' | 'persona-selection' | 'persona-detail' | 'debate' | 'summary' | 'community'
const isCollapsed = ref(false)
const isLoggedIn = ref(false)
const category = ref('ALL')
const selectedIds = ref([])
const detailPersona = ref(null)

// ----- Context state -----
const context = ref({
  situation: '',
  landingPeriods: []
})

// ----- Roles from backend -----
const roles = ref([])
const loadingRoles = ref(false)
const rolesError = ref('')

// ----- Debate state -----
const debateHistory = ref([]) // { personaId: string, text: string }
const debateOptions = ref([])
const isDebating = ref(false)
const debateInput = ref('')

// ----- Preset periods -----
const PRESET_PERIODS = [
  "First time studying abroad",
  "First year after graduation",
  "Early career confusion",
  "Career transition",
  "Around 30 — feeling stuck",
  "Relationship turning point",
  "Creative burnout",
  "Major failure or loss",
  "Starting over in a new city",
  "Becoming independent"
]

// ----- Computed -----
const filteredRoles = computed(() => {
  if (category.value === 'ALL') return roles.value
  // For now, all roles are shown (category filtering can be added later if roles have categories)
  return roles.value
})

const selectedPersonas = computed(() => {
  return roles.value.filter(r => selectedIds.value.includes(r.id))
})

// ----- API calls -----
async function fetchRoles() {
  loadingRoles.value = true
  rolesError.value = ''
  try {
    const res = await fetch(`${API_BASE}/roles/info`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    roles.value = (data.roles || []).map(r => ({
      id: r.name,
      name: r.display_name || r.name,
      role: r.name.toUpperCase(),
      avatar: r.emoji || '🤖',
      worldview: '', // Will be loaded from SOUL.md if needed
      hasKnowledge: r.has_knowledge
    }))
  } catch (e) {
    rolesError.value = `Failed to load roles: ${e}`
  } finally {
    loadingRoles.value = false
  }
}

async function runDebateRound(userInput = '') {
  if (selectedIds.value.length < 2) {
    alert('Please select at least 2 roles')
    return
  }
  
  if (selectedPersonas.value.length < 2) {
    alert('Please select at least 2 roles (some roles may not be loaded yet)')
    return
  }

  isDebating.value = true

  // Add user input to history if provided
  if (userInput.trim()) {
    debateHistory.value.push({ personaId: 'user', text: userInput.trim() })
  }

  try {
    const payload = {
      user_input: userInput.trim() || context.value.situation || 'Start the internal debate.',
      role_names: selectedPersonas.value.map(p => p.id)
    }

    const res = await fetch(`${API_BASE}/debate/round`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      throw new Error(`HTTP ${res.status}: ${errText || res.statusText}`)
    }

    const data = await res.json()

    // Add messages to history
    if (Array.isArray(data.messages)) {
      debateHistory.value.push(...data.messages.map(m => ({
        personaId: m.persona_id,
        text: m.text
      })))
    }

    // Set options
    if (Array.isArray(data.options)) {
      debateOptions.value = data.options
    } else {
      debateOptions.value = []
    }
  } catch (e) {
    console.error(e)
    debateHistory.value.push({
      personaId: 'system',
      text: `Error: ${e.message}`
    })
    debateOptions.value = []
  } finally {
    isDebating.value = false
  }
}

// ----- Handlers -----
function handleNewChat() {
  context.value = { situation: '', landingPeriods: [] }
  selectedIds.value = []
  detailPersona.value = null
  category.value = 'ALL'
  debateHistory.value = []
  debateOptions.value = []
  debateInput.value = ''
  view.value = 'home'
}

function toggleSelect(e, role) {
  e.stopPropagation()
  if (selectedIds.value.includes(role.id)) {
    selectedIds.value = selectedIds.value.filter(id => id !== role.id)
  } else {
    selectedIds.value = [...selectedIds.value, role.id]
  }
}

function handleOptionClick(option) {
  debateOptions.value = []
  runDebateRound(option)
}

function handleDebateInputKeydown(e) {
  if (e.key === 'Enter' && e.target.value.trim()) {
    runDebateRound(e.target.value)
    e.target.value = ''
    debateInput.value = ''
  }
}

function handleInviteToDebate() {
  if (detailPersona.value && !selectedIds.value.includes(detailPersona.value.id)) {
    selectedIds.value.push(detailPersona.value.id)
  }
  view.value = 'persona-selection'
}

// ----- Lifecycle -----
onMounted(() => {
  fetchRoles()
  // Auto-start first round when entering debate view
})

// Auto-start debate when entering debate view
function startDebate() {
  if (selectedIds.value.length < 2) {
    alert('Please select at least 2 roles')
    return
  }
  
  view.value = 'debate'
  debateHistory.value = []
  debateOptions.value = []
  // Start first round automatically
  setTimeout(() => {
    runDebateRound('')
  }, 100)
}
</script>

<template>
  <div class="app-container">
    <!-- Sidebar -->
    <aside :class="['sidebar', { collapsed: isCollapsed }]">
      <div class="sidebar-content">
        <!-- Expand/Collapse -->
        <button
          @click="isCollapsed = !isCollapsed"
          class="sidebar-toggle"
          :title="isCollapsed ? 'Expand Menu' : 'Collapse Menu'"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>

        <!-- New Chat -->
        <button @click="handleNewChat" class="new-chat-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span v-if="!isCollapsed">New Chat</span>
        </button>

        <!-- History -->
        <nav class="sidebar-nav">
          <div v-if="!isCollapsed" class="nav-label">History</div>
          <button v-if="!isCollapsed" class="history-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>"Career confused after..."</span>
          </button>
          <button v-if="!isCollapsed" class="history-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>"Leaving my hometown..."</span>
          </button>
        </nav>
      </div>

      <!-- Bottom Actions -->
      <div class="sidebar-bottom">
        <button class="bottom-item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <span v-if="!isCollapsed">Help</span>
        </button>
        <button class="bottom-item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"></path>
          </svg>
          <span v-if="!isCollapsed">Settings</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Header -->
      <header class="main-header">
        <div class="header-left" @click="view = 'home'">
          <span class="logo-text">LIFEE</span>
        </div>

        <div class="header-right">
          <button
            @click="view = 'community'"
            :class="['nav-link', { active: view === 'community' }]"
          >
            Community
          </button>

          <button v-if="!isLoggedIn" @click="isLoggedIn = true" class="sign-in-btn">
            Sign In
          </button>
          <div v-else class="user-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </div>
        </div>
      </header>

      <!-- Content Area -->
      <main class="content-area">
        <div class="content-inner">
          <!-- Home View -->
          <div v-if="view === 'home'" class="home-view">
            <header class="home-header">
              <h1 class="home-title">LIFEE</h1>
              <p class="home-subtitle">YOUR LIFE & FRIEND COACH</p>
            </header>

            <section class="home-section">
              <div class="situation-card">
                <h2 class="situation-title">"Let them argue, you decide."</h2>
                <textarea
                  v-model="context.situation"
                  class="situation-input"
                  placeholder="Where are you right now? Share your situation..."
                ></textarea>
              </div>

              <div class="periods-section">
                <h3 class="periods-title">When is this landing?</h3>
                <div class="periods-grid">
                  <button
                    v-for="period in PRESET_PERIODS"
                    :key="period"
                    @click="
                      context.landingPeriods = context.landingPeriods.includes(period)
                        ? context.landingPeriods.filter(p => p !== period)
                        : [...context.landingPeriods, period]
                    "
                    :class="['period-btn', { active: context.landingPeriods.includes(period) }]"
                  >
                    {{ period }}
                  </button>
                </div>
              </div>

              <button
                @click="view = 'persona-selection'"
                :disabled="!context.situation"
                class="step-forward-btn"
              >
                Step Forward
              </button>
            </section>
          </div>

          <!-- Persona Selection View -->
          <div v-else-if="view === 'persona-selection'" class="persona-selection-view">
            <div class="selection-header">
              <button @click="view = 'home'" class="back-btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
                Retreat
              </button>
              <div class="panel-count">Panel: {{ selectedIds.length }}</div>
            </div>

            <div class="category-filter">
              <div class="category-filter-inner">
                <button
                  v-for="cat in ['ALL', 'CREATIVE', 'RATIONAL', 'SUPPORT']"
                  :key="cat"
                  @click="category = cat"
                  :class="['category-btn', { active: category === cat }]"
                >
                  {{ cat }}
                </button>
              </div>
            </div>

            <h2 class="selection-title">Assemble the Voices</h2>

            <div v-if="loadingRoles" class="loading">Loading roles...</div>
            <div v-else-if="rolesError" class="error">{{ rolesError }}</div>
            <div v-else class="personas-grid">
              <div
                v-for="role in filteredRoles"
                :key="role.id"
                @click="detailPersona = role; view = 'persona-detail'"
                :class="['persona-card', { selected: selectedIds.includes(role.id) }]"
              >
                <button
                  @click.stop="toggleSelect($event, role)"
                  :class="['select-btn', { active: selectedIds.includes(role.id) }]"
                >
                  <svg v-if="selectedIds.includes(role.id)" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </button>

                <div class="persona-avatar">
                  <span class="avatar-emoji">{{ role.avatar }}</span>
                </div>

                <div class="persona-info">
                  <h4 class="persona-name">{{ role.name }}</h4>
                  <p class="persona-role">{{ role.role }}</p>
                  <p v-if="role.worldview" class="persona-worldview">"{{ role.worldview }}"</p>
                  <span v-if="role.hasKnowledge" class="knowledge-badge">KB</span>
                </div>
              </div>
            </div>

            <div v-if="selectedIds.length >= 2" class="commence-btn-wrapper">
              <button @click="startDebate" class="commence-btn">
                Commence Dialogue
              </button>
            </div>
          </div>

          <!-- Persona Detail View -->
          <div v-else-if="view === 'persona-detail' && detailPersona" class="persona-detail-view">
            <div class="detail-container">
              <div class="detail-header">
                <button @click="view = 'persona-selection'" class="back-btn">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="15 18 9 12 15 6"></polyline>
                  </svg>
                  Back to Selection
                </button>
                <span class="archive-no">Archive No. {{ detailPersona.id.toUpperCase() }}</span>
              </div>

              <div class="detail-main">
                <div class="detail-avatar-card">
                  <div class="detail-avatar">
                    <span class="avatar-large">{{ detailPersona.avatar }}</span>
                  </div>
                </div>
                <div class="detail-intro">
                  <h1 class="detail-name">{{ detailPersona.name }}</h1>
                  <p class="detail-role">{{ detailPersona.role }}</p>
                  <p v-if="detailPersona.worldview" class="detail-worldview">"{{ detailPersona.worldview }}"</p>
                </div>
              </div>

              <div class="detail-footer">
                <p class="detail-note">This role intervenes selectively, observing silence as closely as words.</p>
                <button
                  @click="handleInviteToDebate"
                  :class="['invite-btn', { active: detailPersona && selectedIds.includes(detailPersona.id) }]"
                >
                  {{ detailPersona && selectedIds.includes(detailPersona.id) ? 'IN THE PANEL' : 'INVITE TO DEBATE' }}
                </button>
              </div>
            </div>
          </div>

          <!-- Debate View -->
          <div v-else-if="view === 'debate'" class="debate-view">
            <header class="debate-header">
              <div class="debate-avatars">
                <div
                  v-for="p in selectedPersonas"
                  :key="p.id"
                  class="debate-avatar-small"
                >
                  {{ p.avatar }}
                </div>
              </div>
              <button @click="view = 'summary'" class="stop-btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <rect x="9" y="9" width="6" height="6"></rect>
                </svg>
                STOP & DECIDE
              </button>
            </header>

            <div class="debate-messages-container">
              <div
                v-for="(msg, idx) in debateHistory"
                :key="idx"
                :class="['debate-message', { user: msg.personaId === 'user' }]"
              >
                <div class="message-avatar">
                  <span v-if="msg.personaId === 'user'">👤</span>
                  <span v-else-if="msg.personaId === 'system'">⚠️</span>
                  <span v-else>{{ selectedPersonas.find(p => p.id === msg.personaId)?.avatar || '☁️' }}</span>
                </div>
                <div class="message-content">
                  <span class="message-author">
                    {{ msg.personaId === 'user' ? 'YOU' : msg.personaId === 'system' ? 'SYSTEM' : selectedPersonas.find(p => p.id === msg.personaId)?.name || 'Voice' }}
                  </span>
                  <div class="message-bubble">
                    {{ msg.text }}
                  </div>
                </div>
              </div>

              <div v-if="isDebating" class="debate-loading">
                <div class="loading-avatar"></div>
                <div class="loading-bubble"></div>
              </div>
            </div>

            <div class="debate-input-area">
              <div v-if="debateOptions.length > 0 && !isDebating" class="debate-options">
                <button
                  v-for="(opt, i) in debateOptions"
                  :key="i"
                  @click="handleOptionClick(opt)"
                  class="option-btn"
                >
                  {{ opt }}
                </button>
              </div>

              <div class="debate-input-wrapper">
                <button
                  @click="runDebateRound('')"
                  :disabled="isDebating"
                  class="silent-btn"
                >
                  STAY SILENT
                </button>
                <div class="input-group">
                  <input
                    v-model="debateInput"
                    @keydown="handleDebateInputKeydown"
                    :disabled="isDebating"
                    type="text"
                    placeholder="..."
                    class="debate-input"
                  />
                  <svg class="input-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <!-- Summary View -->
          <div v-else-if="view === 'summary'" class="summary-view">
            <div class="summary-content">
              <div class="summary-emoji">🌱</div>
              <h2 class="summary-title">Your Decision</h2>
              <button @click="handleNewChat" class="new-chapter-btn">
                Start New Chapter
              </button>
            </div>
          </div>

          <!-- Community View -->
          <div v-else-if="view === 'community'" class="community-view">
            <div class="community-content">
              <div class="community-header">
                <h2 class="community-title">Community Archives</h2>
                <p class="community-subtitle">Public Thought Patterns</p>
              </div>
              <div class="community-grid">
                <div v-for="i in 4" :key="i" class="community-card">
                  <div class="community-card-header">
                    <div class="community-icon">🎭</div>
                    <div>
                      <h4>Shared Reflection #{{ i }}204</h4>
                      <p>3 Voices Engaging</p>
                    </div>
                  </div>
                  <p class="community-text">"Exploring the complex tension between safety and personal growth..."</p>
                  <div class="community-footer">
                    <span>Reflected 2 days ago</span>
                    <span>Enter Archive →</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* Import fonts */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Noto+Sans+SC:wght@400;700&display=swap');

/* Base styles */
* {
  box-sizing: border-box;
}

.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-family: 'Noto Sans SC', sans-serif;
  background-color: #FDFBF7;
  color: #5D576B;
}

.font-serif {
  font-family: 'Noto Serif SC', serif;
}

/* Sidebar */
.sidebar {
  width: 260px;
  background-color: #F8F6F2;
  border-right: 1px solid #E8E6E0;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 72px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.sidebar-content::-webkit-scrollbar {
  display: none;
}

.sidebar-toggle {
  padding: 0.75rem;
  margin-bottom: 1rem;
  border-radius: 0.75rem;
  border: none;
  background: transparent;
  color: #98A6D4;
  cursor: pointer;
  transition: background 0.2s;
  align-self: flex-start;
}

.sidebar-toggle:hover {
  background: rgba(255, 255, 255, 0.6);
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  margin-bottom: 2rem;
  background: white;
  border: 1px solid #E8E6E0;
  border-radius: 1rem;
  font-weight: bold;
  color: #5D576B;
  cursor: pointer;
  transition: box-shadow 0.2s;
  font-size: 0.875rem;
}

.sidebar.collapsed .new-chat-btn {
  padding: 0.75rem;
  justify-content: center;
}

.sidebar.collapsed .new-chat-btn span {
  display: none;
}

.new-chat-btn:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.new-chat-btn svg {
  color: #98A6D4;
  flex-shrink: 0;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  font-weight: bold;
  letter-spacing: 0.1em;
  opacity: 0.3;
  padding: 0 1rem;
  margin-bottom: 0.5rem;
}

.sidebar.collapsed .nav-label {
  display: none;
}

.history-item {
  width: 100%;
  text-align: left;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  border: none;
  background: transparent;
  color: rgba(93, 87, 107, 0.6);
  font-size: 0.75rem;
  font-style: italic;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar.collapsed .history-item {
  padding: 0.75rem;
  justify-content: center;
}

.sidebar.collapsed .history-item span {
  display: none;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.6);
}

.sidebar-bottom {
  padding: 1rem;
  border-top: 1px solid #E8E6E0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.bottom-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  border: none;
  background: transparent;
  font-weight: bold;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
  border-radius: 0.75rem;
}

.sidebar.collapsed .bottom-item {
  padding: 0.75rem;
  justify-content: center;
}

.sidebar.collapsed .bottom-item span {
  display: none;
}

.bottom-item:hover {
  background: rgba(255, 255, 255, 0.6);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #FDFBF7;
}

.main-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  background-color: rgba(253, 251, 247, 0.9);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(232, 230, 224, 0.3);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  cursor: pointer;
}

.logo-text {
  font-family: 'Noto Serif SC', serif;
  font-style: italic;
  font-weight: 900;
  font-size: 1.5rem;
  color: #98A6D4;
  letter-spacing: -0.02em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-link {
  border: none;
  background: transparent;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.22em;
  font-weight: 800;
  color: rgba(93, 87, 107, 0.6);
  cursor: pointer;
  padding-bottom: 0.25rem;
  transition: color 0.2s;
}

.nav-link:hover,
.nav-link.active {
  color: #98A6D4;
}

.nav-link.active {
  border-bottom: 2px solid #98A6D4;
}

.sign-in-btn {
  padding: 0.625rem 1.8rem;
  border-radius: 999px;
  border: none;
  background-color: #98A6D4;
  color: white;
  font-size: 0.7rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.22em;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(152, 166, 212, 0.5);
  transition: background 0.2s, transform 0.1s;
}

.sign-in-btn:hover {
  background-color: #8795c4;
}

.sign-in-btn:active {
  transform: scale(0.95);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #98A6D4;
  color: white;
  border: 2px solid white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s;
}

.user-avatar:hover {
  transform: scale(1.05);
}

.content-area {
  flex: 1;
  overflow-y: auto;
}

.content-area::-webkit-scrollbar {
  display: none;
}

.content-inner {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}

/* Home View */
.home-view {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.home-header {
  margin-bottom: 5rem;
  text-align: center;
}

.home-title {
  font-size: 3.75rem;
  font-weight: bold;
  letter-spacing: 0.1em;
  color: #98A6D4;
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  font-style: italic;
}

.home-subtitle {
  font-style: italic;
  font-size: 0.625rem;
  color: #C1C1C1;
  text-transform: uppercase;
  letter-spacing: 0.4em;
  font-weight: 900;
  font-family: 'Noto Sans SC', sans-serif;
}

.home-section {
  max-width: 48rem;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.situation-card {
  background: white;
  padding: 3rem;
  border-radius: 60px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #F0EDEA;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.situation-title {
  font-family: 'Noto Serif SC', serif;
  font-style: italic;
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: #1A1A1A;
}

.situation-input {
  width: 100%;
  height: 10rem;
  padding: 1.5rem;
  background: white;
  border-radius: 1.5rem;
  border: 2px solid #F0EDEA;
  font-size: 1rem;
  line-height: 1.6;
  resize: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  font-family: inherit;
}

.situation-input:focus {
  outline: none;
  border-color: #98A6D4;
  box-shadow: 0 0 0 3px rgba(152, 166, 212, 0.4);
}

.situation-input::placeholder {
  font-style: italic;
}

.periods-section {
  text-align: center;
  padding: 0 1rem;
}

.periods-title {
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: rgba(152, 166, 212, 0.8);
  margin-bottom: 1rem;
}

.periods-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.75rem;
}

.period-btn {
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: bold;
  transition: all 0.2s;
  border: 2px solid #F0EDEA;
  background: white;
  color: rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.period-btn:hover {
  border-color: rgba(152, 166, 212, 0.4);
}

.period-btn.active {
  background-color: #98A6D4;
  color: white;
  border-color: #98A6D4;
  box-shadow: 0 4px 6px rgba(152, 166, 212, 0.3);
  transform: scale(1.05);
}

.step-forward-btn {
  width: 100%;
  padding: 1.5rem;
  background-color: #98A6D4;
  color: white;
  border-radius: 999px;
  font-weight: bold;
  box-shadow: 0 10px 20px rgba(152, 166, 212, 0.5);
  transition: transform 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
}

.step-forward-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.step-forward-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Persona Selection View */
.persona-selection-view {
  animation: fadeIn 0.4s ease-out;
}

.selection-header {
  margin-bottom: 3rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1rem;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.625rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.25em;
  opacity: 0.4;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: opacity 0.2s;
  color: inherit;
}

.back-btn:hover {
  opacity: 1;
}

.panel-count {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.25em;
  opacity: 0.4;
  font-weight: bold;
}

.category-filter {
  display: flex;
  justify-content: center;
  margin-bottom: 4rem;
  padding: 0 1rem;
}

.category-filter-inner {
  display: inline-flex;
  background: rgba(232, 232, 232, 0.5);
  backdrop-filter: blur(8px);
  padding: 0.375rem;
  border-radius: 999px;
  border: 2px solid white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.category-btn {
  padding: 0.625rem 2rem;
  border-radius: 999px;
  font-size: 0.625rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  transition: all 0.3s;
  border: none;
  background: transparent;
  color: rgba(93, 87, 107, 0.6);
  cursor: pointer;
}

.category-btn:hover {
  color: #98A6D4;
}

.category-btn.active {
  background-color: #98A6D4;
  color: white;
  box-shadow: 0 4px 6px rgba(152, 166, 212, 0.3);
  transform: scale(1.05);
}

.selection-title {
  font-size: 2.5rem;
  font-family: 'Noto Serif SC', serif;
  font-style: italic;
  margin-bottom: 4rem;
  color: #5D576B;
  text-align: center;
  letter-spacing: -0.02em;
}

.loading,
.error {
  text-align: center;
  padding: 2rem;
  color: rgba(93, 87, 107, 0.6);
}

.error {
  color: #dc2626;
}

.personas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 2rem;
  margin-bottom: 10rem;
  padding: 0 1rem;
}

.persona-card {
  position: relative;
  padding: 2rem;
  background: white;
  border-radius: 40px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  border: 2px solid #F0EDEA;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  aspect-ratio: 3/4;
  min-height: 320px;
  overflow: hidden;
  cursor: pointer;
}

.persona-card:hover {
  transform: scale(1.03);
}

.persona-card.selected {
  border-color: #98A6D4;
}

.select-btn {
  position: absolute;
  top: 1.5rem;
  right: 1.5rem;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid rgba(0, 0, 0, 0.1);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 30;
}

.persona-card:hover .select-btn {
  border-color: rgba(152, 166, 212, 0.4);
}

.select-btn.active {
  background-color: #98A6D4;
  border-color: #98A6D4;
  box-shadow: 0 4px 6px rgba(152, 166, 212, 0.3);
  transform: scale(1.1);
}

.select-btn svg {
  color: white;
}

.persona-avatar {
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  position: relative;
  margin: 0 auto 1.5rem;
}

.persona-avatar::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 24px;
  transform: rotate(6deg) scale(0.9);
  opacity: 0.4;
}

.avatar-emoji {
  font-size: 2.5rem;
  line-height: 1;
  position: relative;
  z-index: 10;
}

.persona-info {
  margin-top: auto;
  text-align: left;
}

.persona-name {
  font-weight: bold;
  font-size: 1.25rem;
  color: #1A1A1A;
  letter-spacing: -0.02em;
  margin-bottom: 0.25rem;
  line-height: 1.2;
}

.persona-role {
  font-size: 0.5rem;
  text-transform: uppercase;
  font-weight: 900;
  letter-spacing: 0.1em;
  color: #98A6D4;
  margin-bottom: 0.75rem;
}

.persona-worldview {
  font-size: 0.75rem;
  font-style: italic;
  line-height: 1.6;
  color: rgba(0, 0, 0, 0.4);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.knowledge-badge {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  background-color: #e0f7ee;
  color: #0f766e;
  font-size: 0.625rem;
  font-weight: bold;
}

.commence-btn-wrapper {
  position: fixed;
  bottom: 3rem;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 24rem;
  padding: 0 1.5rem;
  z-index: 30;
  animation: fadeIn 0.4s ease-out;
}

.commence-btn {
  width: 100%;
  padding: 1.5rem;
  background: black;
  color: white;
  border-radius: 999px;
  font-weight: bold;
  font-size: 0.625rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s;
  border: none;
  cursor: pointer;
}

.commence-btn:hover {
  transform: scale(1.05);
}

.commence-btn:active {
  transform: scale(0.95);
}

/* Persona Detail View */
.persona-detail-view {
  min-height: calc(100vh - 64px);
  background-color: #E5E3DF;
  padding: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', serif;
  overflow-y: auto;
  animation: fadeIn 0.4s ease-out;
}

.detail-container {
  max-width: 56rem;
  width: 100%;
  background: #FAF9F6;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  border-radius: 2px;
  padding: 3rem;
  position: relative;
  overflow: hidden;
  border: 1px solid #D1CEC7;
}

.detail-container::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 8rem;
  height: 8rem;
  background: rgba(152, 166, 212, 0.05);
  border-radius: 0 0 0 100%;
  pointer-events: none;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3rem;
  position: relative;
  z-index: 10;
  font-family: 'Noto Sans SC', sans-serif;
}

.archive-no {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  opacity: 0.3;
  font-weight: bold;
}

.detail-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  margin-bottom: 4rem;
  position: relative;
}

.detail-avatar-card {
  background: white;
  padding: 1rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #F0EDEA;
  transform: rotate(-2deg);
}

.detail-avatar {
  aspect-ratio: 4/5;
  background: rgba(0, 0, 0, 0.05);
  border-bottom: 1px solid #F0EDEA;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-large {
  font-size: 6rem;
  line-height: 1;
}

.detail-intro {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.detail-name {
  font-size: 3.75rem;
  font-weight: 900;
  letter-spacing: -0.02em;
  color: #1A1A1A;
  line-height: 1;
  margin-bottom: 1rem;
  text-transform: uppercase;
  font-style: italic;
}

.detail-role {
  font-size: 0.875rem;
  font-family: 'Noto Sans SC', sans-serif;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.3em;
  color: #98A6D4;
  margin-bottom: 1.5rem;
}

.detail-worldview {
  font-size: 1.25rem;
  font-style: italic;
  line-height: 1.6;
  color: #5D576B;
}

.detail-footer {
  padding-top: 3rem;
  border-top: 1px solid #D1CEC7;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  align-items: center;
  font-family: 'Noto Sans SC', sans-serif;
}

.detail-note {
  font-size: 0.625rem;
  font-style: italic;
  color: rgba(0, 0, 0, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.invite-btn {
  padding: 1.25rem 3rem;
  border-radius: 999px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.75rem;
  transition: all 0.2s;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
  border: none;
  cursor: pointer;
}

.invite-btn:hover {
  transform: translateY(-4px);
}

.invite-btn:not(.active) {
  background-color: #98A6D4;
  color: white;
}

.invite-btn:not(.active):hover {
  background-color: #8795c4;
}

.invite-btn.active {
  background-color: rgba(0, 0, 0, 0.2);
  color: rgba(0, 0, 0, 0.5);
}

/* Debate View */
.debate-view {
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Noto Sans SC', sans-serif;
  animation: fadeIn 0.4s ease-out;
}

.debate-header {
  padding: 1rem;
  border-bottom: 1px solid #F0EDEA;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 10;
}

.debate-avatars {
  display: flex;
  gap: -0.5rem;
}

.debate-avatar-small {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid white;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  background: white;
  margin-left: -0.5rem;
}

.debate-avatar-small:first-child {
  margin-left: 0;
}

.stop-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: bold;
  color: #E6C6C1;
  padding: 0.5rem 1rem;
  border: 1px solid #E6C6C1;
  border-radius: 999px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.stop-btn:hover {
  background: #E6C6C1;
  color: white;
}

.debate-messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 3rem;
  padding-bottom: 16rem;
}

.debate-messages-container::-webkit-scrollbar {
  display: none;
}

.debate-message {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.debate-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(152, 166, 212, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  background: white;
  flex-shrink: 0;
  font-size: 1.5rem;
}

.debate-message.user .message-avatar {
  border-color: rgba(152, 166, 212, 0.2);
}

.message-content {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.debate-message.user .message-content {
  align-items: flex-end;
}

.message-author {
  font-size: 0.625rem;
  font-weight: bold;
  opacity: 0.3;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.message-bubble {
  padding: 1rem;
  border-radius: 1.5rem;
  font-size: 0.875rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.debate-message:not(.user) .message-bubble {
  background: white;
  border: 1px solid #F0EDEA;
  border-top-left-radius: 0;
}

.debate-message.user .message-bubble {
  background-color: #98A6D4;
  color: white;
  border-top-right-radius: 0;
}

.debate-loading {
  display: flex;
  gap: 1rem;
  margin-top: 2.5rem;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.loading-avatar {
  width: 40px;
  height: 40px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 50%;
}

.loading-bubble {
  height: 48px;
  width: 192px;
  background: white;
  border: 1px solid #F0EDEA;
  border-radius: 1.5rem;
}

.debate-input-area {
  padding: 2rem;
  background: linear-gradient(to top, #FDFBF7, rgba(253, 251, 247, 0));
}

.debate-options {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  animation: fadeIn 0.4s ease-out;
}

.option-btn {
  padding: 0.625rem 1.25rem;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(152, 166, 212, 0.2);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.option-btn:hover {
  background: #98A6D4;
  color: white;
}

.debate-input-wrapper {
  display: flex;
  gap: 1rem;
  max-width: 48rem;
  margin: 0 auto;
}

.silent-btn {
  flex: 1;
  padding: 1.25rem;
  background-color: #98A6D4;
  color: white;
  border-radius: 999px;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.75rem;
  box-shadow: 0 10px 20px rgba(152, 166, 212, 0.5);
  transition: transform 0.2s;
  border: none;
  cursor: pointer;
}

.silent-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.silent-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-group {
  position: relative;
  flex: 2;
}

.debate-input {
  width: 100%;
  height: 3.5rem;
  background: white;
  border-radius: 999px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  padding: 0 3rem 0 2rem;
  font-size: 0.875rem;
  transition: border-color 0.3s;
}

.debate-input:focus {
  outline: none;
  border-color: #98A6D4;
}

.debate-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-icon {
  position: absolute;
  right: 1.5rem;
  top: 50%;
  transform: translateY(-50%);
  color: #98A6D4;
  pointer-events: none;
}

.input-group:focus-within .input-icon {
  opacity: 0;
}

/* Summary View */
.summary-view {
  animation: fadeIn 0.4s ease-out;
}

.summary-content {
  text-align: center;
  padding: 10rem 0;
}

.summary-emoji {
  font-size: 4rem;
  margin-bottom: 3rem;
}

.summary-title {
  font-size: 2.25rem;
  font-family: 'Noto Serif SC', serif;
  font-style: italic;
  margin-bottom: 1.5rem;
  color: #1A1A1A;
}

.new-chapter-btn {
  width: 100%;
  padding: 1.25rem;
  background-color: #98A6D4;
  color: white;
  border-radius: 999px;
  font-weight: bold;
  box-shadow: 0 10px 20px rgba(152, 166, 212, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.75rem;
  border: none;
  cursor: pointer;
  transition: transform 0.2s;
}

.new-chapter-btn:hover {
  transform: translateY(-2px);
}

/* Community View */
.community-view {
  animation: fadeIn 0.4s ease-out;
}

.community-content {
  padding: 3rem;
  max-width: 80rem;
  margin: 0 auto;
}

.community-header {
  margin-bottom: 3rem;
}

.community-title {
  font-size: 3rem;
  font-family: 'Noto Serif SC', serif;
  font-style: italic;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem;
}

.community-subtitle {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.4em;
  opacity: 0.4;
  font-weight: bold;
}

.community-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
}

.community-card {
  background: white;
  padding: 2rem;
  border-radius: 48px;
  border: 1px solid #E8E6E0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s;
}

.community-card:hover {
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
  transform: translateY(-4px);
}

.community-card-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.community-icon {
  width: 48px;
  height: 48px;
  border-radius: 1rem;
  background: #FDFBF7;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  transition: transform 0.2s;
}

.community-card:hover .community-icon {
  transform: scale(1.1);
}

.community-card-header h4 {
  font-weight: bold;
  font-size: 1.125rem;
  color: #1A1A1A;
  margin-bottom: 0.25rem;
}

.community-card-header p {
  font-size: 0.625rem;
  text-transform: uppercase;
  font-weight: bold;
  color: #98A6D4;
  letter-spacing: 0.1em;
}

.community-text {
  font-size: 0.875rem;
  font-style: italic;
  opacity: 0.6;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 2rem;
}

.community-footer {
  padding-top: 1.5rem;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.625rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  opacity: 0.3;
}

.community-footer span:last-child {
  transition: color 0.2s;
}

.community-card:hover .community-footer span:last-child {
  color: #98A6D4;
}

/* Responsive */
@media (max-width: 768px) {
  .personas-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }

  .detail-main {
    grid-template-columns: 1fr;
  }

  .debate-input-wrapper {
    flex-direction: column;
  }
}
</style>
