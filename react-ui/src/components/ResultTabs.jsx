import { Activity, FileText, Microscope, FlaskConical } from 'lucide-react'
import TargetBriefTab from './TargetBriefTab'
import PapersTab from './PapersTab'
import PreprintsTab from './PreprintsTab'
import TrialsTab from './TrialsTab'
import styles from './ResultTabs.module.css'

const TABS = [
  { label: 'Target Brief', icon: Activity },
  { label: 'Papers', icon: FileText },
  { label: 'Preprints', icon: Microscope },
  { label: 'Clinical Trials', icon: FlaskConical },
]

export default function ResultTabs({ results, activeTab, onTabChange }) {
  const counts = [
    results.target_scores?.length,
    results.papers?.length,
    results.preprints?.length,
    results.trials?.length,
  ]

  return (
    <div className={`${styles.container} fade-in`}>
      <div className={styles.tabBar}>
        {TABS.map((tab, i) => {
          const Icon = tab.icon
          return (
            <button
              key={i}
              className={`${styles.tabBtn} ${activeTab === i ? styles.active : ''}`}
              onClick={() => onTabChange(i)}
            >
              <Icon size={15} />
              {tab.label}
              {counts[i] != null && (
                <span className={styles.count}>({counts[i]})</span>
              )}
            </button>
          )
        })}
      </div>

      <div className={styles.panel}>
        {activeTab === 0 && <TargetBriefTab results={results} />}
        {activeTab === 1 && <PapersTab papers={results.papers || []} />}
        {activeTab === 2 && <PreprintsTab preprints={results.preprints || []} />}
        {activeTab === 3 && <TrialsTab trials={results.trials || []} />}
      </div>
    </div>
  )
}
