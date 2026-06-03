import { Sun, Moon, Database, Activity, Target, ShieldCheck } from 'lucide-react'
import styles from './LandingPage.module.css'

export default function LandingPage({ onStart, theme, toggleTheme }) {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <div className={styles.logo}>🧬 PharmaLit</div>
        <div className={styles.navLinks}>
          <button className={styles.navBtn} onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button className={`${styles.navBtn} ${styles.active}`}>Home</button>
          <button className={styles.navBtn} onClick={() => onStart('')}>Analysis</button>
        </div>
      </nav>

      {/* HERO SECTION */}
      <section className={styles.hero}>
        <div className={styles.badge}>🧬 Pharmaceutical R&D Intelligence</div>
        <h1 className={styles.heroTitle}>
          Autonomous R&D Intelligence<br />
          <span className={styles.gradientText}>From clinical literature to validated targets</span>
        </h1>
        <p className={styles.heroDesc}>
          One query turns into a ranked, tool-verified target scoreboard, multi-source evidence, and a cited hypothesis brief. Local-first. IP-safe.
        </p>
        <button className={styles.cta} onClick={() => onStart('')}>
          Start Analysis <span>→</span>
        </button>
      </section>

      {/* STATS SECTION */}
      <div className={styles.stats}>
        {[['5+', 'Data Sources'], ['1–10', 'Transparent Score'], ['~30s', 'Per Query'], ['0 keys', 'For OT & UniProt']].map(([v, l]) => (
          <div key={l} className={styles.statItem}>
            <span className={styles.statVal}>{v}</span>
            <span className={styles.statLbl}>{l}</span>
          </div>
        ))}
      </div>

      {/* SCORING GUIDE SECTION */}
      <section className={styles.scoringGuide}>
        <div className={styles.sectionHeader}>
          <h2>How Target Scoring Works</h2>
          <p>Every gene discovered by the AI is mathematically scored against two public databases to determine its druggability.</p>
        </div>

        <div className={styles.guideGrid}>
          <div className={styles.guideCard}>
            <div className={styles.guideIcon}><Database size={24} /></div>
            <h3>Open Targets (0–7 pts)</h3>
            <ul className={styles.guideList}>
              <li><span className={styles.guidePts}>+5</span> Approved drugs target this protein</li>
              <li><span className={styles.guidePts}>+4</span> Drug candidates in clinical trials</li>
              <li><span className={styles.guidePts}>+3</span> Antibody / Biologic druggable</li>
              <li><span className={styles.guidePts}>+2</span> High-quality small molecules exist</li>
            </ul>
          </div>

          <div className={styles.guideCard}>
            <div className={styles.guideIcon}><ShieldCheck size={24} /></div>
            <h3>UniProt Validation (0–3 pts)</h3>
            <ul className={styles.guideList}>
              <li><span className={styles.guidePts}>+2</span> Confirmed human protein entry</li>
              <li><span className={styles.guidePts}>+1</span> Function is well-documented</li>
            </ul>
          </div>

          <div className={styles.guideCardDark}>
            <div className={styles.guideIconDark}><Target size={24} /></div>
            <h3>Final Score Matrix</h3>
            <div className={styles.matrixRows}>
              <div className={styles.matrixRow}>
                <span className={styles.scoreGreen}>8–10</span>
                <span>Highly Druggable / Established</span>
              </div>
              <div className={styles.matrixRow}>
                <span className={styles.scoreAmber}>5–7</span>
                <span>Emerging Clinical Target</span>
              </div>
              <div className={styles.matrixRow}>
                <span className={styles.scoreRed}>1–4</span>
                <span>Novel / Hard to Drug</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* PERKS SECTION */}
      <section className={styles.perks}>
        <div className={styles.sectionHeader} style={{ marginBottom: '2rem' }}>
          <h2>Why PharmaLit</h2>
        </div>
        <div className={styles.perkGrid}>
          {[
            ['🎯', 'Pharma-native output', 'Ranked, citable target briefs — not a list of papers. Each target gets a structured evidence card.'],
            ['🔒', 'Local-first / IP safe', 'ChromaDB runs on your machine. Your queries and documents never leave your environment.'],
            ['🔄', 'Multi-source fusion', 'PubMed + preprints + ClinicalTrials.gov + RAG in one query.'],
            ['📊', 'Transparent scoring', 'Every score computed by tool — not guessed by AI. Open Targets + UniProt validation.'],
            ['🔍', 'Full audit trail', 'Every tool call, every API response, every step is logged and reproducible.'],
            ['💰', 'Low cost', 'Public APIs for OT, UniProt, Europe PMC, ClinicalTrials — no key required.'],
          ].map(([icon, title, desc]) => (
            <div key={title} className={styles.perkCard}>
              <div className={styles.perkIcon}>{icon}</div>
              <div className={styles.perkTitle}>{title}</div>
              <div className={styles.perkDesc}>{desc}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
