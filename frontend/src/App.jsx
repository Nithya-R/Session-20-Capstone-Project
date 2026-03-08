import { useState } from 'react'
import Login from './components/Login'
import Roadmap from './components/Roadmap'
import Chat from './components/Chat'
import './App.css'

export default function App() {
  const [userId, setUserId] = useState(() => localStorage.getItem('cl_user') || '')
  const [screen, setScreen] = useState('login')
  const [chatTarget, setChatTarget] = useState(null) // { level, mode } or null

  function handleLogin(id) {
    localStorage.setItem('cl_user', id)
    setUserId(id)
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
    setScreen('login')
  }

  return (
    <div className="app">
      {screen === 'login' && <Login onStart={handleLogin} savedUser={userId} />}
      {screen === 'roadmap' && (
        <Roadmap
          userId={userId}
          onContinue={handleContinue}
          onLevelSelect={handleLevelSelect}
          onLogout={handleLogout}
        />
      )}
      {screen === 'chat' && (
        <Chat
          userId={userId}
          target={chatTarget}
          onExit={handleExitChat}
        />
      )}
    </div>
  )
}
