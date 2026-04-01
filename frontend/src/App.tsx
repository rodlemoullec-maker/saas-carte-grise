import { useState, useEffect, useRef } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import ClientPage from './ClientPage'

// ─── Config ─────────────────────────────────────────────────────────────────

const API = 'http://localhost:8001'
const PRO_ID = '00000000-0000-0000-0000-000000000001' // TODO: auth JWT

// ─── Types ──────────────────────────────────────────────────────────────────

interface Dossier {
  id: string; reference: string; type: string | null; status: string
  diagnostic: string | null; vin: string | null; immatriculation: string | null
  client_nom: string | null; client_telephone: string | null
  client_email: string | null; tax_estimate: any | null; created_at: string
}

// ─── Navigation ─────────────────────────────────────────────────────────────

type Page = 'dashboard' | 'workspace' | 'workspace-dossier' | 'dossier-complet' | 'facturation' | 'parametres'

function NavBar({ current, onNav }: { current: Page; onNav: (p: Page) => void }) {
  const items: { id: Page; label: string }[] = [
    { id: 'dashboard', label: 'Tableau de bord' },
    { id: 'workspace', label: 'Espace de travail' },
    { id: 'facturation', label: 'Facturation' },
    { id: 'parametres', label: 'Parametres' },
  ]
  return (
    <nav className="bg-white border-b mb-6">
      <div className="max-w-5xl mx-auto flex gap-1 px-4">
        {items.map(i => (
          <button key={i.id} onClick={() => onNav(i.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
              current === i.id || (i.id === 'workspace' && current === 'workspace-dossier')
                ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {i.label}
          </button>
        ))}
      </div>
    </nav>
  )
}

// ─── Badges ─────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    PENDING: { color: 'bg-gray-100 text-gray-600', label: 'En attente' },
    ATTENTE_CLIENT: { color: 'bg-yellow-100 text-yellow-700', label: 'Attente client' },
    DIAGNOSTIC: { color: 'bg-blue-100 text-blue-700', label: 'Diagnostic' },
    CERFA_GENERE: { color: 'bg-green-100 text-green-700', label: 'Complet' },
    CLOSED: { color: 'bg-red-100 text-red-600', label: 'Annule' },
  }
  const m = map[status] || { color: 'bg-gray-100 text-gray-500', label: status }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${m.color}`}>{m.label}</span>
}

function QualityBadge({ status }: { status: string }) {
  const map: Record<string, string> = { ok: 'bg-green-100 text-green-700', avertissement: 'bg-orange-100 text-orange-700', illisible: 'bg-red-100 text-red-700' }
  const labels: Record<string, string> = { ok: 'Lisible', avertissement: 'Qualite moyenne', illisible: 'Illisible' }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[status] || 'bg-gray-100'}`}>{labels[status] || status}</span>
}

function ScanButton({ dossierId, onUploaded }: { dossierId: string; onUploaded: () => void }) {
  const [scanToken, setScanToken] = useState<string | null>(null)
  const [scanCount, setScanCount] = useState(0)
  const pollRef = useRef<number | null>(null)

  const startScan = async () => {
    const res = await fetch(`${API}/scan/${dossierId}/token`, { method: 'POST' })
    const data = await res.json()
    setScanToken(data.token)
    setScanCount(0)

    // Polling toutes les 3 secondes
    pollRef.current = window.setInterval(async () => {
      const s = await fetch(`${API}/scan/${data.token}/status`).then(r => r.json())
      if (s.count > scanCount) {
        setScanCount(s.count)
        onUploaded()
      }
      if (!s.active) {
        stopScan()
      }
    }, 3000)
  }

  const stopScan = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    setScanToken(null)
  }

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  if (scanToken) {
    const scanUrl = `${window.location.protocol}//${window.location.hostname}:8001/scan/${scanToken}`
    return (
      <div className="mt-4 p-4 bg-white border border-gray-200 rounded-lg text-center">
        <div className="text-sm font-medium text-gray-700 mb-2">Scannez ce QR code avec votre telephone</div>
        <div className="flex justify-center mb-3">
          <QRCodeSVG value={scanUrl} size={180} />
        </div>
        <div className="text-xs text-gray-400 mb-1">Expire dans 10 minutes</div>
        {scanCount > 0 && (
          <div className="text-xs text-green-600 font-medium mb-2">{scanCount} document(s) recu(s)</div>
        )}
        <button onClick={stopScan} className="text-xs text-red-400 hover:text-red-600">Fermer le scanner</button>
      </div>
    )
  }

  return (
    <button onClick={startScan} className="bg-gray-700 hover:bg-gray-800 text-white px-5 py-2 rounded-lg text-sm">
      Scanner (tel)
    </button>
  )
}

function CnitInput({ dossierId, onSaved }: { dossierId: string; onSaved: () => void }) {
  const [cnit, setCnit] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const save = async () => {
    if (!cnit.trim()) return
    setSaving(true)
    await fetch(`${API}/dossiers/${dossierId}/cnit`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cnit: cnit.trim() }),
    })
    setSaving(false)
    setSaved(true)
    onSaved()
  }

  if (saved) return (
    <div className="mb-4 p-4 rounded-lg border bg-green-50 border-green-200">
      <div className="text-sm text-green-800 font-medium">CNIT enregistre : {cnit.toUpperCase()}</div>
      <div className="text-xs text-green-600 mt-1">Il sera inclus dans le Cerfa lors de la generation.</div>
    </div>
  )

  return (
    <div className="mb-4 p-4 rounded-lg border bg-blue-50 border-blue-200">
      <div className="text-sm text-blue-800 font-medium mb-1">CNIT absent du COC (COC europeen)</div>
      <div className="text-xs text-blue-600 mb-3">
        Vous pouvez saisir le CNIT (type mines, champ D.2.1) pour qu'il soit inclus dans le Cerfa.
        Si vous ne le connaissez pas maintenant, vous pourrez le saisir dans le SIV directement.
      </div>
      <div className="flex gap-2">
        <input value={cnit} onChange={e => setCnit(e.target.value.toUpperCase())}
          placeholder="Ex: M10PEUVM5P0A050"
          className="border border-blue-300 rounded px-3 py-1.5 text-sm flex-1 font-mono" />
        <button onClick={save} disabled={!cnit.trim() || saving}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50">
          {saving ? 'Enregistrement...' : 'Enregistrer'}
        </button>
      </div>
    </div>
  )
}

// ─── 1. TABLEAU DE BORD ─────────────────────────────────────────────────────

function Dashboard({ onSelect }: { onSelect: (id: string, status: string) => void }) {
  const [dossiers, setDossiers] = useState<Dossier[]>([])
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetch(`${API}/dossiers/?professionnel_id=${PRO_ID}`).then(r => r.json()).then(setDossiers).catch(() => {})
  }, [])

  const counts = { total: dossiers.length, en_cours: 0, complet: 0, probleme: 0 }
  dossiers.forEach(d => {
    if (d.status === 'CERFA_GENERE') counts.complet++
    else if (d.diagnostic === 'ROUGE') counts.probleme++
    else counts.en_cours++
  })

  const filtered = dossiers.filter(d => {
    if (filter === 'en_cours') return d.status !== 'CERFA_GENERE' && d.diagnostic !== 'ROUGE'
    if (filter === 'complet') return d.status === 'CERFA_GENERE'
    if (filter === 'probleme') return d.diagnostic === 'ROUGE'
    return true
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Tableau de bord</h1>

      {/* Filtres */}
      <div className="flex gap-3 mb-6">
        {[
          { id: 'all', label: `Tous (${counts.total})`, color: 'gray' },
          { id: 'en_cours', label: `En cours (${counts.en_cours})`, color: 'blue' },
          { id: 'complet', label: `Complets (${counts.complet})`, color: 'green' },
          { id: 'probleme', label: `Probleme (${counts.probleme})`, color: 'red' },
        ].map(f => (
          <button key={f.id} onClick={() => setFilter(f.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition ${
              filter === f.id ? `border-${f.color}-500 bg-${f.color}-50 text-${f.color}-700` : 'border-gray-200 text-gray-500'
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      {/* Liste */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">Aucun dossier</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Reference</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Titulaire</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">VIN / Immat</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(d => (
                <tr key={d.id} onClick={() => onSelect(d.id, d.status)} className="hover:bg-blue-50 cursor-pointer">
                  <td className="px-4 py-3 font-mono text-sm">{d.reference}</td>
                  <td className="px-4 py-3 text-sm">{d.client_nom || d.client_telephone || '—'}</td>
                  <td className="px-4 py-3">
                    {d.type ? <span className={`px-2 py-0.5 rounded text-xs font-medium ${d.type === 'VN' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>{d.type}</span>
                    : <span className="text-gray-400 text-xs">Auto-detect</span>}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{d.vin || d.immatriculation || '—'}</td>
                  <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── 2. ESPACE DE TRAVAIL ───────────────────────────────────────────────────

function Workspace({ onOpenDossier }: { onOpenDossier: (id: string) => void }) {
  const [telephone, setTelephone] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [dossiers, setDossiers] = useState<Dossier[]>([])

  useEffect(() => {
    fetch(`${API}/dossiers/?professionnel_id=${PRO_ID}`).then(r => r.json())
      .then(data => setDossiers(data.filter((d: Dossier) => d.status !== 'CERFA_GENERE' && d.status !== 'CLOSED')))
      .catch(() => {})
  }, [])

  const submit = async () => {
    if (!telephone.trim()) { setError('Le numero de portable est obligatoire'); return }
    setLoading(true); setError('')
    const res = await fetch(`${API}/dossiers/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ professionnel_id: PRO_ID, client_telephone: telephone, client_email: email || null }),
    })
    const data = await res.json()
    setLoading(false)
    if (res.ok) { onOpenDossier(data.dossier_id) }
    else { setError(data.detail?.message || data.detail || 'Erreur') }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Espace de travail</h1>

      {/* Nouveau dossier */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-bold text-gray-800 mb-4">+ Nouveau dossier</h2>
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Portable du client *</label>
            <input value={telephone} onChange={e => setTelephone(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2" placeholder="06 12 34 56 78" />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Email (optionnel)</label>
            <input value={email} onChange={e => setEmail(e.target.value)} type="email"
              className="w-full border border-gray-300 rounded-lg px-4 py-2" placeholder="client@exemple.fr" />
          </div>
          <button onClick={submit} disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 whitespace-nowrap">
            {loading ? 'Creation...' : 'Creer'}
          </button>
        </div>
        {error && <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}
      </div>

      {/* Dossiers en cours */}
      {dossiers.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 text-sm font-medium text-gray-600">
            Dossiers en cours ({dossiers.length})
          </div>
          {dossiers.map(d => (
            <div key={d.id} onClick={() => onOpenDossier(d.id)}
              className="px-4 py-3 border-b last:border-0 flex items-center justify-between hover:bg-blue-50 cursor-pointer">
              <div>
                <span className="font-mono text-sm">{d.reference}</span>
                <span className="ml-3 text-sm text-gray-500">{d.client_nom || d.client_telephone}</span>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── 2b. VUE DOSSIER (espace de travail) ────────────────────────────────────

function DossierWorkspace({ dossierId, onBack }: { dossierId: string; onBack: () => void }) {
  const [dossier, setDossier] = useState<any>(null)
  const [checklist, setChecklist] = useState<any>(null)
  const [uploading, setUploading] = useState(false)
  const [lastUpload, setLastUpload] = useState<any>(null)

  const reload = async () => {
    const [d, c] = await Promise.all([
      fetch(`${API}/dossiers/${dossierId}`).then(r => r.json()),
      fetch(`${API}/dossiers/${dossierId}/checklist`).then(r => r.json()).catch(() => null),
    ])
    setDossier(d); setChecklist(c)
  }
  useEffect(() => { reload() }, [dossierId])

  const uploadFile = async (file: File) => {
    setUploading(true)
    const form = new FormData(); form.append('file', file)
    // Le backend classifie automatiquement le document et détermine la source
    form.append('source', 'vendeur')
    try {
      const res = await fetch(`${API}/documents/${dossierId}/upload`, { method: 'POST', body: form })
      setLastUpload(await res.json())
    } catch (e) { /* ignore */ }
    setUploading(false); reload()
  }

  const confirmSendLink = async () => {
    const res = await fetch(`${API}/dossiers/${dossierId}/confirm-send-link`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) alert(data.message)
    else alert(data.detail?.message || 'Erreur')
    reload()
  }

  if (!dossier) return <div className="text-center py-16 text-gray-400">Chargement...</div>

  return (
    <div>
      <button onClick={onBack} className="text-blue-600 hover:text-blue-800 text-sm mb-4">&larr; Retour</button>

      {/* En-tete */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">{dossier.reference}</h2>
          <p className="text-gray-500 text-sm">
            {dossier.type ? <span className={`font-medium ${dossier.type === 'VN' ? 'text-blue-600' : 'text-purple-600'}`}>{dossier.type}</span>
            : <span className="text-gray-400">Type auto-detecte</span>}
            {dossier.client_nom && <> &middot; {dossier.client_nom}</>}
            {dossier.vin && <> &middot; <span className="font-mono text-xs">{dossier.vin}</span></>}
            {dossier.immatriculation && <> &middot; <span className="font-mono text-xs">{dossier.immatriculation}</span></>}
            <> &middot; {dossier.client_telephone}</>
          </p>
        </div>
        <StatusBadge status={dossier.status} />
      </div>

      {/* Checklist */}
      {checklist && (
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h3 className="font-bold text-gray-800 mb-3">Checklist</h3>
          {/* Info client */}
          <div className="mb-2">
            <div className="text-xs font-medium text-gray-400 mb-1">Info client</div>
            {checklist.info_client?.items?.map((item: any) => (
              <div key={item.id} className="flex items-center gap-2 text-sm py-0.5">
                <span className={item.status === 'ok' ? 'text-green-500' : 'text-red-500'}>{item.status === 'ok' ? '✓' : '✗'}</span>
                <span>{item.label}</span>
                {item.value && <span className="text-gray-400 text-xs">— {item.value}</span>}
              </div>
            ))}
          </div>
          {/* Documents vehicule + verrou identification */}
          <div className="mb-2">
            <div className="text-xs font-medium text-gray-400 mb-1 flex items-center flex-wrap gap-2">
              <span>Identification vehicule</span>
              {checklist.documents?.type_detecte && <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">{checklist.documents.type_detecte}</span>}
              {(() => {
                if (!checklist.documents?.ok) {
                  return checklist.documents?.type_detecte
                    ? <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">Incomplet</span>
                    : null
                }
                const cocItem = checklist.documents?.items?.find((d: any) => (d.label || '').toUpperCase() === 'COC')
                if (cocItem && cocItem.has_cnit === false) {
                  return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-semibold">Verifie — CNIT a saisir</span>
                }
                return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-semibold">Verrouille</span>
              })()}
            </div>
            {checklist.documents?.items?.map((item: any, i: number) => (
              <div key={i} className="flex items-center justify-between text-sm py-0.5">
                <div className="flex items-center gap-2">
                  <span className={item.status === 'ok' ? 'text-green-500' : item.status === 'illisible' ? 'text-red-500' : 'text-gray-300'}>
                    {item.status === 'ok' ? '✓' : item.status === 'illisible' ? '✗' : '○'}
                  </span>
                  <span>{item.label || item.type}</span>
                  {item.filename && <span className="text-gray-400 text-xs">— {item.filename}</span>}
                </div>
                {item.status === 'ok' && dossier.status === 'PENDING' && (
                  <div className="flex gap-2">
                    <label className="text-xs text-blue-500 hover:text-blue-700 cursor-pointer">
                      Modifier
                      <input type="file" className="hidden" accept="image/*,application/pdf"
                        onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])} />
                    </label>
                  </div>
                )}
              </div>
            ))}
            {checklist.documents?.missing?.map((item: any, i: number) => (
              <div key={`m-${i}`} className="flex items-center gap-2 text-sm py-0.5">
                <span className={item.required ? 'text-red-400' : 'text-gray-300'}>{item.required ? '!' : '○'}</span>
                <span className={item.required ? 'text-red-600' : 'text-gray-400'}>{item.label} {item.required ? '(manquant)' : '(optionnel)'}</span>
              </div>
            ))}
            {/* Message CNIT si VN et COC sans CNIT */}
            {checklist.documents?.ok && (
              (() => {
                const cocItem = checklist.documents?.items?.find((d: any) => (d.label || '').toUpperCase() === 'COC')
                if (cocItem && cocItem.has_cnit === false) return (
                  <div className="mt-2">
                    <div className="p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700 mb-2">
                      <strong>CNIT absent du COC</strong> (normal pour un COC europeen). Trois options :
                      <ul className="mt-1 ml-3 space-y-0.5" style={{listStyle: 'disc'}}>
                        <li>Saisissez-le ci-dessous maintenant — il sera inclus dans le Cerfa</li>
                        <li>Saisissez-le apres la generation du Cerfa — le Cerfa sera re-genere avec le CNIT</li>
                        <li>Saisissez-le directement dans le SIV lors de la soumission</li>
                      </ul>
                    </div>
                    <CnitInput dossierId={dossierId} onSaved={reload} />
                  </div>
                )
                return null
              })()
            )}
          </div>
          {/* Rappels */}
          {checklist.rappel_assurance && <div className="text-xs text-gray-500 p-2 bg-gray-50 rounded mb-1">Assurance : {checklist.rappel_assurance.message}</div>}

          {/* Documents client — toujours visible mais formulation adaptee */}
          {checklist.client_docs && (
            <div className="mt-3 pt-3 border-t">
              <div className="text-xs font-medium text-gray-400 mb-1">
                Documents client
                {checklist.client_docs.ready_for_diagnostic
                  ? <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">Complet</span>
                  : dossier.status === 'ATTENTE_CLIENT'
                    ? <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">En attente du client</span>
                    : <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">A fournir</span>
                }
              </div>
              {checklist.client_docs.documents?.map((doc: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-sm py-0.5">
                  <div className="flex items-center gap-2">
                    <span className={doc.status === 'ok' ? 'text-green-500' : doc.status === 'illisible' ? 'text-red-500' : 'text-gray-300'}>
                      {doc.status === 'ok' ? '✓' : doc.status === 'illisible' ? '✗' : '○'}
                    </span>
                    <span>{doc.type}</span>
                    {doc.filename && <span className="text-gray-400 text-xs">— {doc.filename}</span>}
                  </div>
                  {doc.status === 'ok' && (dossier.status === 'PENDING' || dossier.status === 'ATTENTE_CLIENT') && (
                    <label className="text-xs text-blue-500 hover:text-blue-700 cursor-pointer">
                      Modifier
                      <input type="file" className="hidden" accept="image/*,application/pdf"
                        onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])} />
                    </label>
                  )}
                </div>
              ))}
              {checklist.client_docs.missing?.map((doc: any, i: number) => (
                <div key={`cm-${i}`} className="flex items-center gap-2 text-sm py-0.5">
                  <span className={doc.required ? 'text-gray-400' : 'text-gray-300'}>{doc.required ? '○' : '○'}</span>
                  <span className={doc.required ? 'text-gray-500' : 'text-gray-400'}>
                    {doc.label}
                    {doc.required
                      ? dossier.status === 'ATTENTE_CLIENT' ? ' (en attente)' : ' (requis)'
                      : ' (optionnel)'
                    }
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Message d'accueil avant premier depot */}
      {dossier.status === 'PENDING' && !checklist?.documents?.type_detecte && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 text-sm text-blue-800">
          <div className="font-semibold mb-3">Pour commencer, deposez vos documents vehicule :</div>
          <div className="space-y-3 text-blue-700">
            <div>
              <div className="font-semibold">Vehicule neuf (VN)</div>
              <div>Deposez le COC et la facture de vente.</div>
            </div>
            <div>
              <div className="font-semibold">Vehicule d'occasion (VO)</div>
              <div>Deposez la carte grise barree si vous l'avez. Vous verrez immediatement si l'identification du vehicule est complete et conforme.</div>
              <div className="mt-1 text-blue-600">Si c'est le client qui la detient, cochez la case ci-dessous. Il pourra la deposer via le lien SMS, mais vous n'aurez la confirmation que lorsqu'il l'aura fait.</div>
              <div className="mt-1">Le certificat de cession sera genere automatiquement avec votre cachet et signature, et envoye au client pour signature via le lien SMS.</div>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-blue-200">
            <label className="flex items-start gap-2 cursor-pointer text-blue-700">
              <input type="checkbox" className="mt-1 rounded" onChange={async (e) => {
                if (e.target.checked) {
                  await fetch(`${API}/dossiers/${dossierId}/cg-chez-client`, { method: 'POST' })
                  reload()
                }
              }} />
              <span>Je n'ai pas la carte grise barree — le client la deposera via le lien SMS</span>
            </label>
          </div>
          <div className="mt-3 pt-3 border-t border-blue-200 text-blue-600 text-xs">
            Les documents client (piece d'identite, permis, justificatif de domicile) peuvent etre deposes par vous ici ou par le client via un lien SMS.
          </div>
        </div>
      )}

      {/* Upload — fichier ou photo — adapte selon l'etat */}
      {(dossier.status === 'PENDING' || dossier.status === 'ATTENTE_CLIENT') && !(checklist?.documents?.ok && checklist?.client_docs?.ready_for_diagnostic) && (
        <div className="border-2 border-dashed rounded-lg p-6 text-center border-blue-200 bg-blue-50/30 mb-4">
          <div className="font-medium text-blue-700 mb-1">
            {!checklist?.documents?.type_detecte
              ? 'Deposer un document'
              : checklist?.documents?.ok
                ? 'Deposer un document client'
                : 'Deposer un document'
            }
          </div>
          <p className="text-xs text-blue-500 mb-3">
            {!checklist?.documents?.type_detecte
              ? 'COC, facture, carte grise barree, CNI, permis, justificatif de domicile...'
              : checklist?.documents?.ok
                ? 'CNI, permis, justificatif de domicile — ou envoyez un lien au client'
                : 'Document vehicule ou client — le systeme identifie automatiquement'
            }
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <input type="file" onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])}
              className="hidden" id="file-vendeur" accept="image/*,application/pdf" />
            <label htmlFor="file-vendeur" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm cursor-pointer">
              {uploading ? 'Analyse...' : 'Fichier'}
            </label>
            <ScanButton dossierId={dossierId} onUploaded={reload} />
          </div>
        </div>
      )}

      {/* Resultat dernier upload */}
      {lastUpload && lastUpload.quality && (
        <div className={`mb-4 p-4 rounded-lg border ${lastUpload.quality.status === 'ok' ? 'bg-green-50 border-green-200' : lastUpload.quality.status === 'illisible' ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-200'}`}>
          <div className="font-medium text-sm mb-1">
            {lastUpload.classification?.type || 'PENDING'} — <QualityBadge status={lastUpload.quality.status} />
            {lastUpload.quality.ocr_confidence != null && <span className="text-gray-400 text-xs ml-2">({(lastUpload.quality.ocr_confidence * 100).toFixed(0)}% {lastUpload.quality.ocr_provider})</span>}
          </div>
          {lastUpload.quality.message && (
            <div className={`text-xs ${lastUpload.quality.status === 'ok' ? 'text-green-600' : 'text-red-600'}`}>{lastUpload.quality.message}</div>
          )}
          {lastUpload.extracted_fields && Object.keys(lastUpload.extracted_fields).length > 0 && (
            <div className="mt-2 text-xs text-gray-600">
              {Object.entries(lastUpload.extracted_fields).filter(([_, v]) => v).slice(0, 5).map(([k, v]) => (
                <span key={k} className="mr-3">{k}: <strong>{String(v)}</strong></span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Alerte CG non barree */}
      {lastUpload?.cg_alerte?.cg_non_barree && (
        <div className="mb-4 p-4 rounded-lg border bg-red-50 border-red-200">
          <div className="font-medium text-sm text-red-800 mb-1">Carte grise non barree</div>
          <div className="text-xs text-red-700">{lastUpload.cg_alerte.message}</div>
        </div>
      )}

      {/* Message de completude */}
      {lastUpload?.completude && (
        <div className={`mb-4 p-4 rounded-lg border ${lastUpload.completude.complet ? 'bg-green-50 border-green-300' : 'bg-amber-50 border-amber-200'}`}>
          <div className="flex items-center gap-2">
            <span className="text-lg">{lastUpload.completude.complet ? '✅' : '📋'}</span>
            <span className={`font-medium text-sm ${lastUpload.completude.complet ? 'text-green-800' : 'text-amber-800'}`}>
              {lastUpload.completude.message}
            </span>
          </div>
          {lastUpload.completude.docs_manquants?.length > 0 && !lastUpload.completude.complet && (
            <div className="mt-2 flex flex-wrap gap-1">
              {lastUpload.completude.docs_manquants.map((d: string, i: number) => (
                <span key={i} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">{d}</span>
              ))}
            </div>
          )}
        </div>
      )}


      {/* Actions */}
      <div className="space-y-3">
        {/* Docs vehicule valides mais docs client manquants → choix */}
        {checklist?.documents?.ok && !checklist?.client_link_ready && dossier.status === 'PENDING' && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-emerald-600 font-bold text-sm">&#10003; Documents vehicule verifies</span>
            </div>
            <p className="text-sm text-gray-600 mb-3">Il manque les documents client. Vous pouvez les deposer vous-meme ci-dessus, ou envoyer un lien au client pour qu'il les depose.</p>
            <button onClick={confirmSendLink} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium">
              Envoyer un lien SMS au client
            </button>
          </div>
        )}
        {/* Tout est pret → envoyer le lien ou generer le cerfa */}
        {checklist?.client_link_ready && dossier.status === 'PENDING' && (
          <button onClick={confirmSendLink} className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-medium">
            Valider et envoyer le lien au client
          </button>
        )}
        {dossier.status === 'ATTENTE_CLIENT' && (
          <div className="text-center py-3 text-gray-500 text-sm bg-yellow-50 rounded-lg">
            En attente des documents du client. Vous serez notifie des qu'il avance. Vous pouvez aussi deposer les documents manquants ci-dessus.
          </div>
        )}
        {dossier.diagnostic === 'VERT' && (
          <>
            <button onClick={() => window.open(`${API}/dossiers/${dossierId}/cerfa`, '_blank')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium">
              Telecharger le Cerfa
            </button>
            {/* CNIT apres generation — si pas encore saisi */}
            {checklist?.documents?.items?.some((d: any) => d.has_cnit === false) && (
              <div className="mt-3">
                <div className="p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700 mb-2">
                  Le CNIT n'est pas inclus dans le Cerfa (COC europeen). Saisissez-le ci-dessous pour re-generer le Cerfa avec le CNIT, ou saisissez-le directement dans le SIV.
                </div>
                <CnitInput dossierId={dossierId} onSaved={reload} />
              </div>
            )}
          </>
        )}
        {dossier.diagnostic === 'ROUGE' && (
          <div className="text-center text-sm text-red-500 py-3 bg-red-50 rounded-lg">
            Des corrections sont necessaires avant de generer le Cerfa
          </div>
        )}
      </div>
    </div>
  )
}

// ─── 2c. VUE DOSSIER COMPLET ────────────────────────────────────────────────

function DossierComplet({ dossierId, onBack }: { dossierId: string; onBack: () => void }) {
  const [admin, setAdmin] = useState<any>(null)

  useEffect(() => {
    fetch(`${API}/dossiers/${dossierId}/admin`).then(r => r.json()).then(setAdmin).catch(() => {})
  }, [dossierId])

  if (!admin) return <div className="text-center py-16 text-gray-400">Chargement...</div>

  const dossierName = [
    admin.client_nom || 'INCONNU',
    admin.type || 'XX',
    admin.reference,
    admin.vin || admin.immatriculation || '',
  ].filter(Boolean).join('_')

  return (
    <div>
      <button onClick={onBack} className="text-blue-600 hover:text-blue-800 text-sm mb-4">&larr; Retour au tableau de bord</button>
      <h2 className="text-xl font-bold mb-1">Dossier complet</h2>
      <p className="text-gray-500 text-sm mb-6 font-mono">{dossierName}</p>

      {/* Infos */}
      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-gray-500">Titulaire :</span> {admin.client_nom} {admin.client_prenom}</div>
          <div><span className="text-gray-500">Type :</span> {admin.type}</div>
          <div><span className="text-gray-500">Reference :</span> {admin.reference}</div>
          <div><span className="text-gray-500">VIN :</span> <span className="font-mono">{admin.vin || '—'}</span></div>
          <div><span className="text-gray-500">Immatriculation :</span> <span className="font-mono">{admin.immatriculation || '—'}</span></div>
          <div><span className="text-gray-500">Cerfa :</span> {admin.cerfa_genere ? '✅ Genere' : '—'}</div>
        </div>
      </div>

      {/* Documents vendeur */}
      <div className="bg-white rounded-lg shadow mb-4">
        <div className="px-4 py-3 border-b bg-blue-50 text-sm font-medium text-blue-700">
          Documents vendeur ({admin.documents_vendeur?.length || 0})
        </div>
        {(admin.documents_vendeur || []).map((doc: any) => (
          <div key={doc.id} className="px-4 py-2 border-b last:border-0 flex items-center justify-between text-sm">
            <div>
              <span className="font-medium">{doc.type}</span>
              <span className="ml-2 text-gray-400 text-xs">{doc.filename}</span>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${doc.status === 'EXTRACTED' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{doc.status}</span>
          </div>
        ))}
      </div>

      {/* Documents client */}
      <div className="bg-white rounded-lg shadow mb-4">
        <div className="px-4 py-3 border-b bg-green-50 text-sm font-medium text-green-700">
          Documents client ({admin.documents_client?.length || 0})
        </div>
        {(admin.documents_client || []).map((doc: any) => (
          <div key={doc.id} className="px-4 py-2 border-b last:border-0 flex items-center justify-between text-sm">
            <div>
              <span className="font-medium">{doc.type}</span>
              <span className="ml-2 text-gray-400 text-xs">{doc.filename}</span>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${doc.status === 'EXTRACTED' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{doc.status}</span>
          </div>
        ))}
        {(!admin.documents_client || admin.documents_client.length === 0) && (
          <div className="px-4 py-3 text-sm text-gray-400">Aucun document client</div>
        )}
      </div>

      {/* Cerfa genere */}
      <div className="bg-white rounded-lg shadow mb-4">
        <div className="px-4 py-3 border-b bg-gray-800 text-sm font-medium text-white">
          Cerfa genere
        </div>
        {admin.cerfa_genere ? (
          <div className="px-4 py-3 flex items-center justify-between">
            <div className="text-sm">
              <span className="font-medium">Cerfa {admin.type === 'VN' ? '13749' : '13750'}</span>
              <span className="ml-2 text-gray-400">Cachet + signature apposes automatiquement</span>
            </div>
            <button onClick={() => window.open(`${API}/dossiers/${dossierId}/cerfa`, '_blank')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm">
              Telecharger
            </button>
          </div>
        ) : (
          <div className="px-4 py-3 text-sm text-gray-400">Cerfa non encore genere</div>
        )}
      </div>

      {/* Telecharger tout */}
      {admin.cerfa_genere && (
        <button onClick={() => window.open(`${API}/dossiers/${dossierId}/download-zip`, '_blank')}
          className="w-full bg-gray-900 hover:bg-gray-800 text-white py-3 rounded-lg font-medium">
          Telecharger le dossier complet (ZIP)
        </button>
      )}
    </div>
  )
}

// ─── 3. FACTURATION ─────────────────────────────────────────────────────────

function Facturation() {
  const [dossiers, setDossiers] = useState<Dossier[]>([])

  useEffect(() => {
    fetch(`${API}/dossiers/?professionnel_id=${PRO_ID}`).then(r => r.json()).then(setDossiers).catch(() => {})
  }, [])

  const traites = dossiers.filter(d => d.status === 'CERFA_GENERE')
  const enCours = dossiers.filter(d => d.status !== 'CERFA_GENERE' && d.status !== 'CLOSED')
  const montantDu = traites.length * 12 // TODO: 12 moto / 14 voiture
  const verrou = enCours.length >= 5

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Facturation</h1>

      {/* Dossiers a regler */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-bold text-gray-800 mb-4">Dossiers a regler</h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{enCours.length}/5</div>
            <div className="text-sm text-blue-700">Dossiers en cours</div>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-700">{traites.length}</div>
            <div className="text-sm text-gray-600">Dossiers traites</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">{montantDu} EUR</div>
            <div className="text-sm text-orange-700">Montant du</div>
          </div>
        </div>
        {verrou && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-4">
            Reglez vos dossiers en cours pour pouvoir en creer de nouveaux.
          </div>
        )}
        {montantDu > 0 && (
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium">
            Payer {montantDu} EUR
          </button>
        )}
      </div>

      {/* Mes factures */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-bold text-gray-800 mb-4">Mes factures</h2>
        <div className="text-center py-8 text-gray-400 text-sm">
          Aucune facture pour le moment
        </div>
      </div>

      {/* Export */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-bold text-gray-800 mb-4">Export comptable</h2>
        <div className="flex gap-3">
          <button className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
            Telecharger CSV
          </button>
          <button className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
            Telecharger PDF
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── 4. PARAMETRES ──────────────────────────────────────────────────────────

function ProfilCommerce({ profil, onUpdate }: { profil: any; onUpdate: (p: any) => void }) {
  const [editingContact, setEditingContact] = useState(false)
  const [tel, setTel] = useState(profil.telephone_commerce || '')
  const [email, setEmail] = useState(profil.email_commerce || '')
  const [saving, setSaving] = useState(false)

  const saveContact = async () => {
    setSaving(true)
    await fetch(`${API}/professionnel/profil?pro_id=${PRO_ID}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nom_commerce: profil.nom_commerce, adresse: profil.adresse,
        telephone_commerce: tel, email_commerce: email || null,
        assurance_flotte_vn: profil.assurance_flotte_vn, assurance_flotte_vo: profil.assurance_flotte_vo,
        demander_assurance_client_vn: profil.demander_assurance_client_vn,
        demander_assurance_client_vo: profil.demander_assurance_client_vo,
      }),
    })
    const updated = await fetch(`${API}/professionnel/profil?pro_id=${PRO_ID}`).then(r => r.json())
    onUpdate(updated)
    setSaving(false); setEditingContact(false)
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="font-bold text-gray-800 mb-2">Profil commerce</h2>
      <p className="text-xs text-gray-400 mb-4">Ces infos apparaitront dans le SMS recu par vos clients pour qu'ils sachent qui les contacte.</p>

      {/* Infos extraites du Kbis — non modifiables */}
      <div className="p-3 bg-gray-50 rounded-lg mb-4">
        <div className="text-xs font-medium text-gray-400 mb-2">Extraits automatiquement du Kbis</div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-gray-500">Nom commerce :</span> <strong>{profil.nom_commerce || '—'}</strong></div>
          <div><span className="text-gray-500">Adresse :</span> <strong>{profil.adresse || '—'}</strong></div>
          <div><span className="text-gray-500">SIRET :</span> <strong>{profil.siret || '—'}</strong></div>
          <div><span className="text-gray-500">Raison sociale :</span> <strong>{profil.raison_sociale || '—'}</strong></div>
        </div>
        <p className="text-xs text-blue-600 mt-2">Pour modifier ces informations, deposez un Kbis mis a jour dans la section Documents ci-dessous.</p>
      </div>

      {/* Contact — modifiable */}
      <div className="text-xs font-medium text-gray-400 mb-2">Coordonnees de contact (modifiables)</div>
      {editingContact ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Telephone *</label>
              <input value={tel} onChange={e => setTel(e.target.value)} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
              <input value={email} onChange={e => setEmail(e.target.value)} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={saveContact} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50">
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
            <button onClick={() => setEditingContact(false)} className="text-gray-500 hover:text-gray-700 px-4 py-2 text-sm">Annuler</button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <div className="grid grid-cols-2 gap-4 text-sm flex-1">
            <div><span className="text-gray-500">Telephone :</span> {profil.telephone_commerce || '—'}</div>
            <div><span className="text-gray-500">Email :</span> {profil.email_commerce || '—'}</div>
          </div>
          <button onClick={() => setEditingContact(true)} className="text-blue-600 hover:text-blue-800 text-sm ml-4">Modifier</button>
        </div>
      )}
    </div>
  )
}

function Parametres() {
  const [profil, setProfil] = useState<any>(null)

  useEffect(() => {
    fetch(`${API}/professionnel/profil?pro_id=${PRO_ID}`).then(r => r.json()).then(setProfil).catch(() => {})
  }, [])

  if (!profil) return <div className="text-center py-16 text-gray-400">Chargement...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Parametres</h1>
      <p className="text-gray-500 mb-6">Configurez votre espace. Ces informations seront utilisees pour communiquer avec vos clients.</p>

      <ProfilCommerce profil={profil} onUpdate={setProfil} />

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-bold text-gray-800 mb-2">Documents obligatoires</h2>
        <p className="text-xs text-gray-400 mb-4">Votre cachet et signature seront apposes automatiquement sur tous les documents (Cerfa, facture, cession). Le Kbis identifie votre structure.</p>
        <div className="space-y-3 text-sm">
          {[
            { key: 'cachet', label: 'Cachet commercial', uploaded: profil.cachet_uploaded, endpoint: 'cachet', desc: 'Photo de votre cachet sur fond blanc' },
            { key: 'signature', label: 'Signature', uploaded: profil.signature_uploaded, endpoint: 'signature', desc: 'Photo de votre signature sur fond blanc' },
            { key: 'kbis', label: 'Kbis', uploaded: profil.kbis_uploaded, endpoint: 'kbis', desc: 'Kbis de moins de 3 mois — SIREN et raison sociale extraits automatiquement' },
          ].map(doc => (
            <div key={doc.key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className={doc.uploaded ? 'text-green-500' : 'text-red-500'}>{doc.uploaded ? '✓' : '✗'}</span>
                <div>
                  <div className="font-medium">{doc.label}</div>
                  <div className="text-xs text-gray-400">{doc.desc}</div>
                </div>
              </div>
              <div>
                <input type="file" className="hidden" id={`upload-${doc.key}`}
                  accept="image/*,application/pdf"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    const form = new FormData(); form.append('file', file)
                    await fetch(`${API}/professionnel/profil/${doc.endpoint}?pro_id=${PRO_ID}`, { method: 'POST', body: form })
                    // Recharger le profil
                    fetch(`${API}/professionnel/profil?pro_id=${PRO_ID}`).then(r => r.json()).then(setProfil)
                  }} />
                <label htmlFor={`upload-${doc.key}`}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs cursor-pointer">
                  {doc.uploaded ? 'Modifier' : 'Deposer'}
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-bold text-gray-800 mb-4">Assurance flotte</h2>
        <p className="text-sm text-gray-500 mb-4">
          Votre assurance flotte couvre-t-elle les vehicules vendus en attendant la finalisation au SIV ?
          Cette info nous permet d'adapter la demande d'attestation d'assurance aupres de vos clients.
        </p>
        <div className="space-y-4 text-sm">
          {/* VN */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <span className={profil.assurance_flotte_vn ? 'text-green-500' : 'text-red-400'}>{profil.assurance_flotte_vn ? '✓' : '✗'}</span>
              <strong>Vehicules neufs (VN)</strong> — {profil.assurance_flotte_vn ? 'couvert par la flotte' : 'non couvert'}
            </div>
            {!profil.assurance_flotte_vn && (
              <div className="ml-6 text-gray-500">
                Demander l'attestation au client : {profil.demander_assurance_client_vn
                  ? <span className="text-blue-600 font-medium">oui, automatiquement</span>
                  : <span className="text-gray-400">non, vous gerez directement</span>}
              </div>
            )}
          </div>
          {/* VO */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <span className={profil.assurance_flotte_vo ? 'text-green-500' : 'text-red-400'}>{profil.assurance_flotte_vo ? '✓' : '✗'}</span>
              <strong>Vehicules d'occasion (VO)</strong> — {profil.assurance_flotte_vo ? 'couvert par la flotte' : 'non couvert'}
            </div>
            {!profil.assurance_flotte_vo && (
              <div className="ml-6 text-gray-500">
                Demander l'attestation au client : {profil.demander_assurance_client_vo
                  ? <span className="text-blue-600 font-medium">oui, automatiquement</span>
                  : <span className="text-gray-400">non, vous gerez directement</span>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── MAIN APP ───────────────────────────────────────────────────────────────

export default function App() {
  // Detecter si on est sur une page client (URL contient /client/)
  const path = window.location.pathname
  const clientMatch = path.match(/\/client\/(.+)/)
  if (clientMatch) {
    return <ClientPage token={clientMatch[1]} />
  }

  return <ProApp />
}

function ProApp() {
  const [page, setPage] = useState<Page>('dashboard')
  const [selectedId, setSelectedId] = useState('')

  const handleDashboardSelect = (id: string, status: string) => {
    setSelectedId(id)
    if (status === 'CERFA_GENERE') setPage('dossier-complet')
    else setPage('workspace-dossier')
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <NavBar current={page} onNav={setPage} />
      <div className="max-w-5xl mx-auto px-4 pb-12">
        {page === 'dashboard' && <Dashboard onSelect={handleDashboardSelect} />}
        {page === 'workspace' && <Workspace onOpenDossier={id => { setSelectedId(id); setPage('workspace-dossier') }} />}
        {page === 'workspace-dossier' && <DossierWorkspace dossierId={selectedId} onBack={() => setPage('workspace')} />}
        {page === 'dossier-complet' && <DossierComplet dossierId={selectedId} onBack={() => setPage('dashboard')} />}
        {page === 'facturation' && <Facturation />}
        {page === 'parametres' && <Parametres />}
      </div>
    </div>
  )
}
