import { useState } from 'react'
import styles from './ScoreCard.module.css'

const SCORE_COLORS = [
  { max: 3, color: '#ef4444', bg: '#fee2e2' },
  { max: 6, color: '#f59e0b', bg: '#fef3c7' },
  { max: 8, color: '#10b981', bg: '#d1fae5' },
  { max: 10, color: '#0ea5e9', bg: '#e0f2fe' },
]

function getColor(score) {
  return SCORE_COLORS.find(c => score <= c.max) || SCORE_COLORS[SCORE_COLORS.length - 1]
}

function ScoreGauge({ score }) {
  const { color } = getColor(score)
  const pct = (score / 10)
  // SVG half-circle gauge
  const cx = 40, cy = 40, r = 30
  const circumference = Math.PI * r
  const dash = pct * circumference

  return (
    <svg width="80" height="48" viewBox="0 0 80 48" className={styles.gauge}>
      {/* Track */}
      <path
        d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke="#e2e8f0" strokeWidth="7" strokeLinecap="round"
      />
      {/* Fill */}
      <path
        d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
        strokeDasharray={`${dash} ${circumference}`}
        style={{ transition: 'stroke-dasharray 0.6s ease' }}
      />
      {/* Score text */}
      <text x={cx} y={cy - 2} textAnchor="middle" fontSize="13" fontWeight="800" fill={color} fontFamily="Inter">
        {score}
      </text>
      <text x={cx} y={cx + 6} textAnchor="middle" fontSize="8" fill="#94a3b8" fontFamily="Inter">
        /10
      </text>
    </svg>
  )
}

function TractabilityBadge({ label }) {
  const lower = (label || '').toLowerCase()
  let cls = styles.badgeUnk
  if (lower.includes('small molecule')) cls = styles.badgeSm
  else if (lower.includes('biologic') || lower.includes('antibody')) cls = styles.badgeAb
  else if (lower.includes('druggable')) cls = styles.badgeSm

  return <span className={`${styles.badge} ${cls}`}>{label || 'Unclassified'}</span>
}

export default function ScoreCard({ target }) {
  const [open, setOpen] = useState(false)
  const [fnExpanded, setFnExpanded] = useState(false)
  const score = target.score ?? target.composite_score ?? 0
  const gene = target.gene || target.symbol || '?'
  const tractability = target.tractability_label || target.tractability || ''
  const uniprot = target.uniprot_id || ''
  const ensembl = target.ensembl_id || ''
  const fn = target.protein_function || target.function || ''
  const breakdown = target.breakdown || []

  return (
    <div className={`${styles.card} fade-in`}>
      {/* Header row */}
      <div className={styles.header}>
        <div className={styles.left}>
          <ScoreGauge score={score} />
          <div className={styles.info}>
            <div className={styles.gene}>{gene}</div>
            <div className={styles.label}>Gene Target</div>
            {uniprot && <div className={styles.ids}>UniProt: {uniprot}</div>}
            {ensembl && <div className={styles.ids}>Ensembl: {ensembl}</div>}
          </div>
        </div>
        <TractabilityBadge label={tractability} />
      </div>

      {/* Function snippet */}
      {fn && (
        <p className={styles.fn} onClick={() => setFnExpanded(f => !f)} style={{ cursor: 'pointer' }}>
          {fnExpanded ? fn : (fn.length > 180 ? fn.slice(0, 180) + '… (Click to read more)' : fn)}
        </p>
      )}

      {/* Origin hint */}
      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '0.75rem', fontStyle: 'italic' }}>
        *This target was extracted by AI from the aggregate context of the papers and preprints above.
      </div>

      {/* Score breakdown toggle */}
      <button className={styles.breakdownToggle} onClick={() => setOpen(o => !o)}>
        <span>Score breakdown</span>
        <span>{open ? '▲' : '▼'}</span>
      </button>

      {open && breakdown.length > 0 && (
        <div className={styles.breakdownBody}>
          {breakdown.map((row, i) => (
            <div key={i} className={styles.bdRow}>
              <span className={styles.bdLabel}>{row.criterion || row.label}</span>
              <span className={styles.bdSource}>{row.source}</span>
              <span className={styles.bdPts}>+{row.points ?? row.pts}</span>
            </div>
          ))}
          <div className={styles.bdTotal}>
            <span>Total</span>
            <span>{score}/10</span>
          </div>
        </div>
      )}
    </div>
  )
}
