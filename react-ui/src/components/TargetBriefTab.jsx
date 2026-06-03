import { useState } from 'react'
import ScoreCard from './ScoreCard'
import styles from './TargetBriefTab.module.css'

export default function TargetBriefTab({ results }) {
  const scores = results.target_scores || []
  const brief = results.brief || ''
  const [briefOpen, setBriefOpen] = useState(false)

  return (
    <div className={styles.wrap}>
      {scores.length > 0 ? (
        <div className={styles.cardList}>
          {scores.map((target, i) => (
            <ScoreCard key={i} target={target} />
          ))}
        </div>
      ) : (
        <div className={styles.empty}>No targets scored for this query.</div>
      )}

      {brief && (
        <div className={styles.briefSection}>
          <button
            className={styles.briefToggle}
            onClick={() => setBriefOpen(o => !o)}
          >
            <span>📄 Hypothesis Brief</span>
            <span>{briefOpen ? '▲' : '▼'}</span>
          </button>
          {briefOpen && (
            <div
              className={styles.briefBody}
              dangerouslySetInnerHTML={{ __html: markdownToHtml(brief) }}
            />
          )}
        </div>
      )}
    </div>
  )
}

// Simple markdown → html
function markdownToHtml(md) {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
}
