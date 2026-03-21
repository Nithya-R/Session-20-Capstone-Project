import { useState } from 'react'
import Login from './components/Login'
import Roadmap from './components/Roadmap'
import Chat from './components/Chat'
import AdminPanel from './components/AdminPanel'
import NewsPanel from './components/NewsPanel'
import Simulator from './components/Simulator'
import './App.css'

export default function App() {
  const [userId, setUserId] = useState(() => localStorage.getItem('cl_user') || '')
  const [isAdmin, setIsAdmin] = useState(() => localStorage.getItem('cl_user') === 'admin')
  const [screen, setScreen] = useState('login')
  const [chatTarget, setChatTarget] = useState(null) // { level, mode } or null

  function handleLogin(id, admin = false) {
    localStorage.setItem('cl_user', id)
    setUserId(id)
    setIsAdmin(admin)
    setScreen('roadmap')
  }

  function handleContinue() {
    setChatTarget(null)
    setScreen('chat')
  }

  function handleLevelSelect(level, mode) {
    setChatTarget({ level, mode })
    setScreen('chat')
  }

  function handleExitChat() {
    setChatTarget(null)
    setScreen('roadmap')
  }

  function handleLogout() {
    localStorage.removeItem('cl_user')
    setUserId('')
    setIsAdmin(false)
    setScreen('login')
  }

  return (
    <div className="app">
      {screen === 'login' && <Login onStart={handleLogin} savedUser={userId} />}
      {screen === 'roadmap' && (
        <Roadmap
          userId={userId}
          isAdmin={isAdmin}
          onContinue={handleContinue}
          onLevelSelect={handleLevelSelect}
          onLogout={handleLogout}
          onNews={() => setScreen('news')}
          onAdmin={() => setScreen('admin')}
          onSimulator={() => setScreen('simulator')}
        />
      )}
      {screen === 'chat' && (
        <Chat
          userId={userId}
          target={chatTarget}
          onExit={handleExitChat}
        />
      )}
      {screen === 'admin' && (
        <AdminPanel
          onBack={() => setScreen('roadmap')}
        />
      )}
      {screen === 'news' && (
        <NewsPanel
          userId={userId}
          onBack={() => setScreen('roadmap')}
        />
      )}
      {screen === 'simulator' && (
        <div style={{ position: 'relative' }}>
          <button 
            onClick={() => setScreen('roadmap')} 
            style={{ position: 'absolute', top: '1rem', left: '1rem', zIndex: 10, padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', cursor: 'pointer' }}
          >
            ← Back to Roadmap
          </button>
          <Simulator userId={userId} />
        </div>
      )}
    </div>
  )
}
