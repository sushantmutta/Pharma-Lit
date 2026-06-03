import { useState, useEffect, useRef, useCallback } from 'react'
import { Sparkles, Send, FlaskConical, FileText, Microscope, TestTube } from 'lucide-react'
import PipelineBox from './PipelineBox'
import ResultTabs from './ResultTabs'
import NavBar from './NavBar'
import styles from './AnalysisPage.module.css'

const API_BASE = ''

export default function AnalysisPage({ initialQuery, onHome, theme, toggleTheme }) {
  const [query, setQuery] = useState(initialQuery || '')
  const [daysBack, setDaysBack] = useState(180)
  const [maxPapers, setMaxPapers] = useState(20)
  const [fetchFresh, setFetchFresh] = useState(true)
  const [loading, setLoading] = useState(false)
  const [steps, setSteps] = useState([])
  const [results, setResults] = useState(null)
  const [activeTab, setActiveTab] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const inputRef = useRef(null)

  // Auto-run if initial query provided
  useEffect(() => {
    if (initialQuery?.trim()) {
      runAnalysis(initialQuery.trim())
    }
    inputRef.current?.focus()
  }, [])

  const runAnalysis = useCallback(async (q) => {
    const finalQuery = (q || query).trim()
    if (!finalQuery || loading) return

    setLoading(true)
    setSteps([])
    setResults(null)
    setActiveTab(0)

    // Simulate step-by-step updates while waiting for real response
    const stepMessages = [
      { icon: '🏥', text: 'Searching ClinicalTrials.gov...' },
      { icon: '📚', text: 'Fetching PubMed papers...' },
      { icon: '🧪', text: 'Searching preprints (bioRxiv/medRxiv)...' },
      { icon: '🧬', text: 'Discovering candidate targets...' },
      { icon: '📊', text: 'Scoring targets for druggability...' },
      { icon: '🤖', text: 'Generating hypothesis brief...' },
    ]
    let stepIdx = 0
    const stepTimer = setInterval(() => {
      if (stepIdx < stepMessages.length) {
        setSteps(prev => [...prev, { ...stepMessages[stepIdx], status: 'running' }])
        stepIdx++
      }
    }, 400)

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: finalQuery,
          days_back: daysBack,
          max_papers: maxPapers,
          fetch_fresh: fetchFresh,
        }),
      })
      clearInterval(stepTimer)

      if (!res.ok) throw new Error(`API error: ${res.status}`)
      const data = await res.json()

      // Mark all steps done
      setSteps(stepMessages.map(s => ({ ...s, status: 'done' })))
      setResults(data)
    } catch (err) {
      clearInterval(stepTimer)
      setSteps(prev => [...prev, { icon: '❌', text: `Error: ${err.message}`, status: 'error' }])
    } finally {
      setLoading(false)
    }
  }, [query, daysBack, maxPapers, fetchFresh, loading])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      runAnalysis()
    }
  }

  return (
    <div className={styles.page}>
      <NavBar onHome={onHome} theme={theme} toggleTheme={toggleTheme} />

      <div className={styles.content}>
        {/* Pipeline Status Box */}
        {(loading || steps.length > 0) && (
          <PipelineBox steps={steps} loading={loading} query={query} />
        )}

        {/* Empty state */}
        {!loading && steps.length === 0 && !results && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>🧬</div>
            <h2>Start your analysis</h2>
            <p>Enter a disease area, target, or drug class in the search bar below.</p>
            <div className={styles.exampleQueries}>
              {[
                'GLP1 receptor agonist obesity',
                'KRAS mutant NSCLC lung cancer',
                'NASH FXR agonist liver fibrosis',
                'EGFR inhibitor resistance breast cancer',
              ].map(ex => (
                <button
                  key={ex}
                  className={styles.exampleChip}
                  onClick={() => { setQuery(ex); runAnalysis(ex) }}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Results Tabs */}
        {results && (
          <ResultTabs
            results={results}
            activeTab={activeTab}
            onTabChange={setActiveTab}
          />
        )}
      </div>

      {/* Floating Query Bar */}
      <div className={styles.queryBarWrap}>
        <div className={styles.queryBar}>
          {/* Settings row */}
          <div className={styles.settingsRow}>
            <label className={styles.settingItem}>
              <span>Days back</span>
              <input
                type="number" min="1" max="1825"
                value={daysBack}
                onChange={e => setDaysBack(Number(e.target.value))}
                className={styles.smallInput}
              />
            </label>
            <label className={styles.settingItem}>
              <span>Max papers</span>
              <input
                type="number" min="1" max="50"
                value={maxPapers}
                onChange={e => setMaxPapers(Number(e.target.value))}
                className={styles.smallInput}
              />
            </label>
            <label className={styles.settingItem} style={{ cursor: 'pointer' }}>
              <span>Fetch fresh</span>
              <div
                className={`${styles.toggle} ${fetchFresh ? styles.toggleOn : ''}`}
                onClick={() => setFetchFresh(f => !f)}
              >
                <div className={styles.toggleThumb} />
              </div>
            </label>
          </div>

          {/* Input row */}
          <div className={styles.inputRow}>
            <Sparkles size={20} color="#0ea5e9" style={{ flexShrink: 0 }} />
            <input
              ref={inputRef}
              type="text"
              placeholder="Ask about drug targets, clinical trials, or research papers..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className={styles.queryInput}
              disabled={loading}
            />
            <button
              className={styles.analyzeBtn}
              onClick={() => runAnalysis()}
              disabled={loading || !query.trim()}
            >
              {loading
                ? <span className="spinner" style={{ width: 16, height: 16 }} />
                : <><Send size={14} /> Analyze</>
              }
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
