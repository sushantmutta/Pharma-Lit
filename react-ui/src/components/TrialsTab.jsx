import styles from './TrialsTab.module.css'

export default function TrialsTab({ trials }) {
  if (!trials.length) return <div className={styles.empty}>No clinical trials found.</div>
  return (
    <div className={styles.list}>
      {trials.map((t, i) => <TrialCard key={i} trial={t} />)}
    </div>
  )
}

function TrialCard({ trial }) {
  const title = trial.title || trial.brief_title || 'Untitled Trial'
  const status = trial.status || trial.overall_status || ''
  const phase = trial.phase || ''
  const condition = trial.condition || trial.conditions || ''
  const nctId = trial.nct_id || trial.id || ''
  const sponsor = trial.sponsor || ''
  const url = nctId ? `https://clinicaltrials.gov/study/${nctId}` : '#'

  const statusClass =
    status.toLowerCase().includes('recruit') ? styles.statusRecruit :
    status.toLowerCase().includes('active') ? styles.statusActive :
    styles.statusOther

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={`${styles.statusBadge} ${statusClass}`}>{status || 'N/A'}</span>
        <div className={styles.title}>{title}</div>
      </div>
      <div className={styles.meta}>
        {phase && <span><strong>Phase:</strong> {phase}</span>}
        {condition && <span><strong>Condition:</strong> {typeof condition === 'string' ? condition : condition.join(', ')}</span>}
        {sponsor && <span><strong>Sponsor:</strong> {sponsor}</span>}
        {nctId && <span><strong>NCT ID:</strong> <a href={url} target="_blank" rel="noreferrer">{nctId}</a></span>}
      </div>
    </div>
  )
}
