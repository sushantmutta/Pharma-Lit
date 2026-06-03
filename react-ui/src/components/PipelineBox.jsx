import { Sparkles } from 'lucide-react'
import styles from './PipelineBox.module.css'

export default function PipelineBox({ steps, loading }) {
  return (
    <div className={`${styles.box} fade-in`}>
      <div className={styles.header}>
        <Sparkles size={16} color="#0ea5e9" />
        <span>Analysis Pipeline</span>
      </div>
      <div className={styles.steps}>
        {steps.map((step, i) => (
          <div key={i} className={`${styles.pill} ${styles[step.status]}`}>
            <span className={`${styles.dot} ${step.status === 'running' && loading && i === steps.length - 1 ? styles.dotPulse : ''}`} />
            <span className={styles.pillIcon}>{step.icon}</span>
            <span className={styles.pillText}>{step.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
