import { Sun, Moon } from 'lucide-react'
import styles from './NavBar.module.css'

export default function NavBar({ onHome, theme, toggleTheme }) {
  return (
    <nav className={styles.nav}>
      <button className={styles.logo} onClick={onHome}>
        <span className={styles.logoIcon}>🧬</span>
        <span>PharmaLit</span>
      </button>
      <div className={styles.links}>
        <button className={styles.link} style={{ display: 'flex', alignItems: 'center' }} onClick={toggleTheme}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button className={styles.link} onClick={onHome}>Home</button>
        <button className={`${styles.link} ${styles.active}`}>Analysis</button>
      </div>
    </nav>
  )
}
