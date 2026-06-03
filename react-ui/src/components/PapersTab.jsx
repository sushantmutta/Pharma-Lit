import { useState } from 'react'
import styles from './PapersTab.module.css'

export default function PapersTab({ papers }) {
  if (!papers.length) return <div className={styles.empty}>No papers found.</div>
  return (
    <div className={styles.list}>
      {papers.map((p, i) => <PaperCard key={i} paper={p} type="PubMed" />)}
    </div>
  )
}

export function PreprintsTab({ preprints }) {
  if (!preprints.length) return <div className={styles.empty}>No preprints found.</div>
  return (
    <div className={styles.list}>
      {preprints.map((p, i) => <PaperCard key={i} paper={p} type="Preprint" />)}
    </div>
  )
}

function PaperCard({ paper, type }) {
  const [open, setOpen] = useState(false)
  const title = paper.title || 'Untitled'
  const authors = paper.authors || paper.author || ''
  const journal = paper.journal || paper.source || ''
  const year = paper.year || paper.date || ''
  const abstract = paper.abstract || ''
  const pmid = paper.pmid || paper.id || ''
  const idLabel = type === 'Preprint' ? 'Preprint ID' : 'PMID'
  const url = paper.url || (pmid ? (type === 'Preprint' ? `https://europepmc.org/article/PPR/${pmid}` : `https://pubmed.ncbi.nlm.nih.gov/${pmid}`) : '#')
  const doi = paper.doi && paper.doi !== 'N/A' ? paper.doi : ''

  return (
    <div className={`${styles.card} ${open ? styles.open : ''}`} onClick={() => setOpen(o => !o)}>
      <div className={styles.summary}>
        <span className={`${styles.badge} ${type === 'PubMed' ? styles.badgePubmed : styles.badgePreprint}`}>
          {type}
        </span>
        <div className={styles.title}>{title}</div>
        <span className={styles.chevron}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className={styles.detail} onClick={e => e.stopPropagation()}>
          <div className={styles.meta}>
            {authors && <span><strong>Authors:</strong> {typeof authors === 'string' ? authors : authors.join(', ')}</span>}
            {journal && <span><strong>Journal:</strong> {journal}</span>}
            {year && <span><strong>Year:</strong> {year}</span>}
            {pmid && <span><strong>{idLabel}:</strong> <a href={url} target="_blank" rel="noreferrer">{pmid}</a></span>}
            {doi && <span><strong>DOI:</strong> <a href={`https://doi.org/${doi}`} target="_blank" rel="noreferrer">{doi}</a></span>}
          </div>
          {abstract && <p className={styles.abstract}>{abstract}</p>}
        </div>
      )}
    </div>
  )
}
