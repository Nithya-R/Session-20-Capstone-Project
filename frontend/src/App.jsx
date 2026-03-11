import { useState } from 'react'
import Login from './components/Login'
import Roadmap from './components/Roadmap'
import Chat from './components/Chat'
import AdminPanel from './components/AdminPanel'
import NewsPanel from './components/NewsPanel'
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
    </div>
  )
}
