import { useState, useCallback, useEffect } from 'react'
import LandingPage from './components/LandingPage'
import AnalysisPage from './components/AnalysisPage'

export default function App() {
  const [page, setPage] = useState('landing') // 'landing' | 'analysis'
  const [initialQuery, setInitialQuery] = useState('')
  const [theme, setTheme] = useState('light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  const goToAnalysis = useCallback((query = '') => {
    setInitialQuery(query)
    setPage('analysis')
  }, [])

  const goToLanding = useCallback(() => setPage('landing'), [])

  return (
    <div style={{ height: '100%' }}>
      <div style={{ display: page === 'landing' ? 'block' : 'none', height: '100%' }}>
        <LandingPage onStart={goToAnalysis} theme={theme} toggleTheme={toggleTheme} />
      </div>
      <div style={{ display: page === 'analysis' ? 'block' : 'none', height: '100%' }}>
        <AnalysisPage initialQuery={initialQuery} onHome={goToLanding} theme={theme} toggleTheme={toggleTheme} />
      </div>
    </div>
  )
}
