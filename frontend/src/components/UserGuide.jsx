import { useState } from 'react'
import './UserGuide.css'

const STEPS = [
  {
    emoji: '🏛️',
    title: 'Welcome to Civic Lens',
    body: 'Your personal guide to understanding how India is governed. Learn civics through bite-sized lessons, smart quizzes, and a personalised learning path — all at your own pace.',
  },
  {
    emoji: '📋',
    title: 'Start with a Placement Quiz',
    body: 'When you first log in, you\'ll take a short 7-question placement quiz. Based on your answers, we figure out which level is the right starting point for you. No pressure — it\'s just to help us help you better!',
  },
  {
    emoji: '🗺️',
    title: 'Your Learning Roadmap',
    body: 'After the quiz, you\'ll see your personalised roadmap — 15 levels of civic knowledge. Your current level is highlighted. All levels below your assessed level are unlocked for free exploration.',
  },
  {
    emoji: '📖',
    title: 'Lessons in Flash-Cards',
    body: 'Each lesson is broken into short, focused cards — one topic at a time. Use "Next" and "Previous" to move through them. Have a question? Just type it and your tutor will answer it based on what you\'re reading.',
  },
  {
    emoji: '✏️',
    title: 'Level Quizzes',
    body: 'Once you\'ve read a lesson, take the level quiz (7 questions). Score 6 or more to unlock the next level. If you don\'t pass, the level gets flagged for revision and you can try again.',
  },
  {
    emoji: '🔍',
    title: 'Review Your Answers',
    body: 'After every quiz, you can review all questions — see which ones you got right (green) and which you got wrong (red), along with the correct answer. Great for learning from mistakes!',
  },
  {
    emoji: '🔥',
    title: 'Track Your Progress',
    body: 'Your XP bar fills up as you complete levels. Check the left panel on the roadmap to see recently completed levels. Your progress is saved automatically — you can pick up right where you left off.',
  },
]

export default function UserGuide({ onClose }) {
  const [step, setStep] = useState(0)
  const current = STEPS[step]
  const isLast  = step === STEPS.length - 1

  return (
    <div className="ug-overlay" onClick={onClose}>
      <div className="ug-modal" onClick={e => e.stopPropagation()}>

        {/* Progress dots */}
        <div className="ug-dots">
          {STEPS.map((_, i) => (
            <button
              key={i}
              className={`ug-dot ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
              onClick={() => setStep(i)}
            />
          ))}
        </div>

        {/* Card */}
        <div className="ug-card">
          <div className="ug-emoji">{current.emoji}</div>
          <h2 className="ug-title">{current.title}</h2>
          <p className="ug-body">{current.body}</p>
        </div>

        {/* Counter */}
        <div className="ug-counter">{step + 1} of {STEPS.length}</div>

        {/* Nav */}
        <div className="ug-nav">
          <button
            className="ug-btn ug-btn-ghost"
            onClick={() => step > 0 ? setStep(s => s - 1) : onClose()}
          >
            {step === 0 ? 'Close' : '← Back'}
          </button>

          <button
            className={`ug-btn ${isLast ? 'ug-btn-primary' : 'ug-btn-next'}`}
            onClick={() => isLast ? onClose() : setStep(s => s + 1)}
          >
            {isLast ? "Let's go! 🚀" : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  )
}
