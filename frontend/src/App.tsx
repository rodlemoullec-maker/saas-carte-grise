import { useState, useEffect, useRef } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import ClientPage from './ClientPage'
import PublicClientPage from './PublicClientPage'
import {
  LayoutDashboard, Briefcase, CreditCard, Settings, ArrowLeft,
  Upload, ScanLine, Check, X, Circle, AlertCircle, AlertTriangle,
  FileText, Download, Pencil, Send, Lock, Unlock, Phone,
  Mail, Building2, ChevronRight, Zap, Clock, CheckCircle2,
  XCircle, Loader2, Info, Package, User, Search, Filter,
  CircleDot, ShieldCheck, Stamp, PenTool, FileCheck, Archive,
} from 'lucide-react'

// ─── Config ─────────────────────────────────────────────────────────────────

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001'
const MAINTENANCE = true   // ← mettre false pour désactiver la maintenance

// ─── Auth helpers ──────────────────────────────────────────────────────────

function getToken(): string | null { return localStorage.getItem('autodoc_token') }
function getProId(): string | null { return localStorage.getItem('autodoc_pro_id') }
function saveAuth(token: string, proId: string) {
  localStorage.setItem('autodoc_token', token)
  localStorage.setItem('autodoc_pro_id', proId)
}
function clearAuth() {
  localStorage.removeItem('autodoc_token')
  localStorage.removeItem('autodoc_pro_id')
}


// ─── Types ──────────────────────────────────────────────────────────────────

interface Dossier {
  id: string; reference: string; type: string | null; status: string
  diagnostic: string | null; vin: string | null; immatriculation: string | null
  client_nom: string | null; client_telephone: string | null
  client_email: string | null; tax_estimate: any | null
  created_by_source: string; created_at: string
}

// ─── Navigation ─────────────────────────────────────────────────────────────

type Page = 'dashboard' | 'workspace' | 'workspace-dossier' | 'dossier-complet' | 'facturation' | 'parametres'

function NavBar({ current, onNav, badge, onLogout }: { current: Page; onNav: (p: Page) => void; badge?: string; onLogout?: () => void }) {
  const items: { id: Page; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Tableau de bord', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'workspace', label: 'Espace de travail', icon: <Briefcase className="w-4 h-4" /> },
    { id: 'facturation', label: 'Facturation', icon: <CreditCard className="w-4 h-4" /> },
    { id: 'parametres', label: 'Paramètres', icon: <Settings className="w-4 h-4" /> },
  ]
  return (
    <nav className="sticky top-0 z-50 bg-white/92 backdrop-blur-xl border-b border-slate-200/80 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
      <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-16">
        <a href="/" className="flex items-center gap-2.5 group">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-emerald flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
          </span>
          <span className="text-lg font-extrabold text-navy tracking-tight">AutoDoc Pro</span>
          {badge && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary-light text-primary border border-blue-200">{badge}</span>
          )}
        </a>
        <div className="flex gap-1 items-center">
          {items.map(i => {
            const active = current === i.id || (i.id === 'workspace' && current === 'workspace-dossier')
            return (
              <button key={i.id} onClick={() => onNav(i.id)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                  active
                    ? 'bg-primary/8 text-primary'
                    : 'text-navy-600 hover:text-navy hover:bg-slate-100'
                }`}>
                {i.icon}
                {i.label}
              </button>
            )
          })}
          {onLogout && (
            <button onClick={onLogout}
              className="ml-2 px-3 py-2 text-xs text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all">
              Deconnexion
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}

// ─── Badges ─────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
    PENDING: { color: 'bg-slate-100 text-slate-600 border-slate-200', label: 'En attente', icon: <Clock className="w-3 h-3" /> },
    ATTENTE_CLIENT: { color: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Attente client', icon: <User className="w-3 h-3" /> },
    DIAGNOSTIC: { color: 'bg-primary-light text-primary border-blue-200', label: 'Diagnostic', icon: <Search className="w-3 h-3" /> },
    CERFA_GENERE: { color: 'bg-emerald-light text-emerald border-emerald/20', label: 'Complet', icon: <CheckCircle2 className="w-3 h-3" /> },
    CLOSED: { color: 'bg-red-50 text-red-600 border-red-200', label: 'Annulé', icon: <XCircle className="w-3 h-3" /> },
  }
  const m = map[status] || { color: 'bg-slate-100 text-slate-500 border-slate-200', label: status, icon: <Circle className="w-3 h-3" /> }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${m.color}`}>
      {m.icon}{m.label}
    </span>
  )
}

function QualityBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
    ok: { color: 'bg-emerald-light text-emerald-dark border-emerald/20', label: 'Lisible', icon: <CheckCircle2 className="w-3 h-3" /> },
    avertissement: { color: 'bg-orange-50 text-orange-700 border-orange-200', label: 'Qualité moyenne', icon: <AlertTriangle className="w-3 h-3" /> },
    illisible: { color: 'bg-red-50 text-red-700 border-red-200', label: 'Illisible', icon: <XCircle className="w-3 h-3" /> },
  }
  const m = map[status] || { color: 'bg-slate-100 text-slate-500 border-slate-200', label: status, icon: <Circle className="w-3 h-3" /> }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${m.color}`}>
      {m.icon}{m.label}
    </span>
  )
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
      <div className="mt-4 p-5 bg-white border border-slate-200 rounded-2xl text-center shadow-sm">
        <div className="text-sm font-semibold text-navy mb-3">Scannez ce QR code avec votre téléphone</div>
        <div className="flex justify-center mb-3">
          <div className="p-3 bg-white rounded-xl border border-slate-100 shadow-sm">
            <QRCodeSVG value={scanUrl} size={180} />
          </div>
        </div>
        <div className="text-xs text-slate-400 mb-2">Expire dans 10 minutes</div>
        {scanCount > 0 && (
          <div className="inline-flex items-center gap-1.5 text-xs text-emerald font-semibold mb-2 bg-emerald-light px-3 py-1 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {scanCount} document(s) reçu(s)
          </div>
        )}
        <div>
          <button onClick={stopScan} className="text-xs text-slate-400 hover:text-red-500 transition-colors">
            Fermer le scanner
          </button>
        </div>
      </div>
    )
  }

  return (
    <button onClick={startScan}
      className="inline-flex items-center gap-2 bg-navy-800 hover:bg-navy text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 hover:shadow-lg">
      <ScanLine className="w-4 h-4" />
      Scanner (tél)
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
    <div className="mb-4 p-4 rounded-2xl border bg-emerald-light/50 border-emerald/20">
      <div className="flex items-center gap-2 text-sm text-emerald-dark font-semibold">
        <CheckCircle2 className="w-4 h-4" />
        CNIT enregistré : {cnit.toUpperCase()}
      </div>
      <div className="text-xs text-emerald-dark/70 mt-1 ml-6">Il sera inclus dans le Cerfa lors de la génération.</div>
    </div>
  )

  return (
    <div className="mb-4 p-4 rounded-2xl border bg-primary-light/50 border-blue-200">
      <div className="flex items-center gap-2 text-sm text-primary font-semibold mb-1">
        <Info className="w-4 h-4" />
        CNIT absent du COC (COC européen)
      </div>
      <div className="text-xs text-primary/70 mb-3 ml-6">
        Vous pouvez saisir le CNIT (type mines, champ D.2.1) pour qu'il soit inclus dans le Cerfa.
        Si vous ne le connaissez pas maintenant, vous pourrez le saisir dans le SIV directement.
      </div>
      <div className="flex gap-2 ml-6">
        <input value={cnit} onChange={e => setCnit(e.target.value.toUpperCase())}
          placeholder="Ex: M10PEUVM5P0A050"
          className="border border-blue-300 rounded-lg px-3 py-2 text-sm flex-1 font-mono bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
        <button onClick={save} disabled={!cnit.trim() || saving}
          className="bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 transition-all">
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
    fetch(`${API}/dossiers/?professionnel_id=${getProId()}`).then(r => r.json()).then(setDossiers).catch(() => {})
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

  const filterItems = [
    { id: 'all', label: `Tous (${counts.total})`, icon: <Filter className="w-3.5 h-3.5" />, active: 'bg-navy text-white border-navy shadow-md', inactive: 'border-slate-200 text-slate-500 hover:border-slate-300' },
    { id: 'en_cours', label: `En cours (${counts.en_cours})`, icon: <Clock className="w-3.5 h-3.5" />, active: 'bg-primary text-white border-primary shadow-md', inactive: 'border-slate-200 text-slate-500 hover:border-primary/30 hover:text-primary' },
    { id: 'complet', label: `Complets (${counts.complet})`, icon: <CheckCircle2 className="w-3.5 h-3.5" />, active: 'bg-emerald text-white border-emerald shadow-md', inactive: 'border-slate-200 text-slate-500 hover:border-emerald/30 hover:text-emerald' },
    { id: 'probleme', label: `Problème (${counts.probleme})`, icon: <AlertCircle className="w-3.5 h-3.5" />, active: 'bg-red-500 text-white border-red-500 shadow-md', inactive: 'border-slate-200 text-slate-500 hover:border-red-300 hover:text-red-500' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-extrabold text-navy tracking-tight mb-8">Tableau de bord</h1>

      {/* Filtres */}
      <div className="flex gap-2 mb-6">
        {filterItems.map(f => (
          <button key={f.id} onClick={() => setFilter(f.id)}
            className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold border transition-all duration-200 ${
              filter === f.id ? f.active : f.inactive
            }`}>
            {f.icon}
            {f.label}
          </button>
        ))}
      </div>

      {/* Liste */}
      {filtered.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <Briefcase className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <p className="text-sm">Aucun dossier</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Référence</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Titulaire</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">VIN / Immat</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(d => (
                <tr key={d.id} onClick={() => onSelect(d.id, d.status)}
                  className="hover:bg-primary-light/30 cursor-pointer transition-colors group">
                  <td className="px-5 py-3.5 font-mono text-sm text-navy font-medium">{d.reference}</td>
                  <td className="px-5 py-3.5 text-sm text-navy-700">
                    <span>{d.client_nom || d.client_telephone || '—'}</span>
                    {d.created_by_source === 'CLIENT' && (
                      <span className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        <User className="w-2.5 h-2.5" /> Client public
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    {d.type ? (
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        d.type === 'VN' ? 'bg-primary-light text-primary border-blue-200' : 'bg-purple-50 text-purple-700 border-purple-200'
                      }`}>
                        <Package className="w-3 h-3" />{d.type}
                      </span>
                    ) : <span className="text-slate-400 text-xs">Auto-détecté</span>}
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{d.vin || d.immatriculation || '—'}</td>
                  <td className="px-5 py-3.5"><StatusBadge status={d.status} /></td>
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
    fetch(`${API}/dossiers/?professionnel_id=${getProId()}`).then(r => r.json())
      .then(data => setDossiers(data.filter((d: Dossier) => d.status !== 'CERFA_GENERE' && d.status !== 'CLOSED')))
      .catch(() => {})
  }, [])

  const submit = async () => {
    if (!telephone.trim()) { setError('Le numéro de portable est obligatoire'); return }
    setLoading(true); setError('')
    const res = await fetch(`${API}/dossiers/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ professionnel_id: getProId(), client_telephone: telephone, client_email: email || null }),
    })
    const data = await res.json()
    setLoading(false)
    if (res.ok) { onOpenDossier(data.dossier_id) }
    else { setError(data.detail?.message || data.detail || 'Erreur') }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold text-navy tracking-tight mb-8">Espace de travail</h1>

      {/* Nouveau dossier */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-4">
          <div className="w-6 h-6 rounded-lg bg-emerald-light flex items-center justify-center">
            <FileText className="w-3.5 h-3.5 text-emerald" />
          </div>
          Nouveau dossier
        </h2>
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-navy-700 mb-1.5">
              <Phone className="w-3.5 h-3.5 inline mr-1.5 text-slate-400" />
              Portable du client *
            </label>
            <input value={telephone} onChange={e => setTelephone(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" placeholder="06 12 34 56 78" />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-navy-700 mb-1.5">
              <Mail className="w-3.5 h-3.5 inline mr-1.5 text-slate-400" />
              Email (optionnel)
            </label>
            <input value={email} onChange={e => setEmail(e.target.value)} type="email"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" placeholder="client@exemple.fr" />
          </div>
          <button onClick={submit} disabled={loading}
            className="inline-flex items-center gap-2 bg-emerald hover:bg-emerald-dark text-white px-6 py-2.5 rounded-xl font-semibold text-sm disabled:opacity-50 whitespace-nowrap transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
            {loading ? 'Création...' : 'Créer'}
          </button>
        </div>
        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
          </div>
        )}
      </div>

      {/* Dossiers en cours */}
      {dossiers.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/80 text-sm font-semibold text-navy-700 flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-primary" />
            Dossiers en cours ({dossiers.length})
          </div>
          {dossiers.map(d => (
            <div key={d.id} onClick={() => onOpenDossier(d.id)}
              className="px-5 py-3.5 border-b last:border-0 flex items-center justify-between hover:bg-primary-light/30 cursor-pointer transition-colors group">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm font-medium text-navy">{d.reference}</span>
                <span className="text-sm text-slate-500">{d.client_nom || d.client_telephone}</span>
                {d.created_by_source === 'CLIENT' && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <User className="w-2.5 h-2.5" /> Client public
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={d.status} />
                <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-primary transition-colors" />
              </div>
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

  if (!dossier) return (
    <div className="text-center py-20 text-slate-400">
      <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin text-primary" />
      <p className="text-sm">Chargement...</p>
    </div>
  )

  return (
    <div>
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-primary hover:text-primary-dark text-sm font-medium mb-5 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Retour
      </button>

      {/* En-tête */}
      <div className="flex items-center justify-between mb-6 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
        <div>
          <h2 className="text-xl font-extrabold text-navy tracking-tight">{dossier.reference}</h2>
          <p className="text-slate-500 text-sm mt-1 flex items-center gap-2 flex-wrap">
            {dossier.type ? (
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${
                dossier.type === 'VN' ? 'bg-primary-light text-primary border-blue-200' : 'bg-purple-50 text-purple-700 border-purple-200'
              }`}>
                <Package className="w-3 h-3" />{dossier.type}
              </span>
            ) : <span className="text-slate-400 text-xs">Type auto-détecté</span>}
            {dossier.client_nom && <span className="text-navy-700">{dossier.client_nom}</span>}
            {dossier.vin && <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">{dossier.vin}</span>}
            {dossier.immatriculation && <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">{dossier.immatriculation}</span>}
            <span className="text-slate-400">{dossier.client_telephone}</span>
          </p>
        </div>
        <StatusBadge status={dossier.status} />
      </div>

      {/* Checklist */}
      {checklist && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 mb-4">
          <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
            <FileCheck className="w-4 h-4 text-primary" />
            Checklist
          </h3>

          {/* Info client */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Info client</div>
            {checklist.info_client?.items?.map((item: any) => (
              <div key={item.id} className="flex items-center gap-2.5 text-sm py-1">
                {item.status === 'ok'
                  ? <CheckCircle2 className="w-4 h-4 text-emerald flex-shrink-0" />
                  : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                }
                <span className="text-navy-700">{item.label}</span>
                {item.value && <span className="text-slate-400 text-xs">— {item.value}</span>}
              </div>
            ))}
          </div>

          {/* Documents véhicule + verrou identification */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center flex-wrap gap-2">
              <span>Identification véhicule</span>
              {checklist.documents?.type_detecte && (
                <span className="px-2 py-0.5 bg-primary-light text-primary rounded-full text-xs font-semibold border border-blue-200">
                  {checklist.documents.type_detecte}
                </span>
              )}
              {(() => {
                if (!checklist.documents?.ok) {
                  return checklist.documents?.type_detecte
                    ? <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full text-xs font-semibold border border-amber-200">
                        <Unlock className="w-3 h-3" /> Incomplet
                      </span>
                    : null
                }
                const cocItem = checklist.documents?.items?.find((d: any) => (d.label || '').toUpperCase() === 'COC')
                if (cocItem && cocItem.has_cnit === false) {
                  return <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-light text-primary rounded-full text-xs font-semibold border border-blue-200">
                    <ShieldCheck className="w-3 h-3" /> Vérifié — CNIT à saisir
                  </span>
                }
                return <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-light text-emerald rounded-full text-xs font-semibold border border-emerald/20">
                  <Lock className="w-3 h-3" /> Verrouillé
                </span>
              })()}
            </div>
            {checklist.documents?.items?.map((item: any, i: number) => (
              <div key={i} className="flex items-center justify-between text-sm py-1.5">
                <div className="flex items-center gap-2.5">
                  {item.status === 'ok'
                    ? <CheckCircle2 className="w-4 h-4 text-emerald flex-shrink-0" />
                    : item.status === 'illisible'
                      ? <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                      : <Circle className="w-4 h-4 text-slate-300 flex-shrink-0" />
                  }
                  <span className="text-navy-700">{item.label || item.type}</span>
                  {item.filename && <span className="text-slate-400 text-xs">— {item.filename}</span>}
                  {item.source === 'client' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200 font-medium">client</span>
                  )}
                </div>
                {item.status === 'ok' && dossier.status === 'PENDING' && (
                  <label className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary-dark cursor-pointer font-medium transition-colors">
                    <Pencil className="w-3 h-3" /> Modifier
                    <input type="file" className="hidden" accept="image/*,application/pdf"
                      onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])} />
                  </label>
                )}
              </div>
            ))}
            {checklist.documents?.missing?.map((item: any, i: number) => (
              <div key={`m-${i}`} className="flex items-center gap-2.5 text-sm py-1.5">
                {item.required
                  ? <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  : <Circle className="w-4 h-4 text-slate-300 flex-shrink-0" />
                }
                <span className={item.required ? 'text-red-600 font-medium' : 'text-slate-400'}>
                  {item.label} {item.required ? '(manquant)' : '(optionnel)'}
                </span>
              </div>
            ))}
            {/* Message CNIT si VN et COC sans CNIT */}
            {checklist.documents?.ok && (
              (() => {
                const cocItem = checklist.documents?.items?.find((d: any) => (d.label || '').toUpperCase() === 'COC')
                if (cocItem && cocItem.has_cnit === false) return (
                  <div className="mt-3">
                    <div className="p-3 bg-primary-light/50 border border-blue-200 rounded-xl text-xs text-primary mb-2">
                      <strong>CNIT absent du COC</strong> (normal pour un COC européen). Trois options :
                      <ul className="mt-1.5 ml-4 space-y-0.5" style={{listStyle: 'disc'}}>
                        <li>Saisissez-le ci-dessous maintenant — il sera inclus dans le Cerfa</li>
                        <li>Saisissez-le après la génération du Cerfa — le Cerfa sera re-généré avec le CNIT</li>
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
          {checklist.rappel_assurance && (
            <div className="text-xs text-slate-500 p-3 bg-slate-50 rounded-xl mb-2 flex items-start gap-2">
              <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-400" />
              Assurance : {checklist.rappel_assurance.message}
            </div>
          )}

          {/* Documents client — toujours visible mais formulation adaptée */}
          {checklist.client_docs && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <span>Documents client</span>
                {checklist.client_docs.client_verrouille
                  ? <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-light text-emerald rounded-full text-xs font-semibold border border-emerald/20">
                      <Lock className="w-3 h-3" /> Verrouillé
                    </span>
                  : checklist.client_docs.ready_for_diagnostic
                    ? <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-light text-emerald rounded-full text-xs font-semibold border border-emerald/20">
                        <CheckCircle2 className="w-3 h-3" /> Complet
                      </span>
                    : dossier.status === 'ATTENTE_CLIENT'
                      ? <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full text-xs font-semibold border border-amber-200">
                          <Clock className="w-3 h-3" /> En attente du client
                        </span>
                      : <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full text-xs font-semibold border border-slate-200">
                          <CircleDot className="w-3 h-3" /> À fournir
                      </span>
                }
              </div>
              {checklist.client_docs.documents?.map((doc: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-sm py-1.5">
                  <div className="flex items-center gap-2.5">
                    {doc.status === 'ok'
                      ? <CheckCircle2 className="w-4 h-4 text-emerald flex-shrink-0" />
                      : doc.status === 'illisible'
                        ? <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                        : <Circle className="w-4 h-4 text-slate-300 flex-shrink-0" />
                    }
                    <span className="text-navy-700">{doc.type}</span>
                    {doc.filename && <span className="text-slate-400 text-xs">— {doc.filename}</span>}
                    {doc.source === 'vendeur' && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary-light text-primary border border-blue-200 font-medium">pro</span>
                    )}
                  </div>
                  {doc.status === 'ok' && (dossier.status === 'PENDING' || dossier.status === 'ATTENTE_CLIENT') && (
                    <label className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary-dark cursor-pointer font-medium transition-colors">
                      <Pencil className="w-3 h-3" /> Modifier
                      <input type="file" className="hidden" accept="image/*,application/pdf"
                        onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])} />
                    </label>
                  )}
                </div>
              ))}
              {checklist.client_docs.missing?.map((doc: any, i: number) => (
                <div key={`cm-${i}`} className="flex items-center gap-2.5 text-sm py-1.5">
                  <Circle className="w-4 h-4 text-slate-300 flex-shrink-0" />
                  <span className={doc.required ? 'text-slate-500' : 'text-slate-400'}>
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

      {/* Message d'accueil avant premier dépôt */}
      {dossier.status === 'PENDING' && !checklist?.documents?.type_detecte && (
        <div className="bg-gradient-to-br from-primary-light/60 to-blue-50 border border-blue-200 rounded-2xl p-5 mb-4">
          <div className="font-bold text-navy mb-3 flex items-center gap-2">
            <Info className="w-5 h-5 text-primary" />
            Pour commencer, déposez vos documents véhicule :
          </div>
          <div className="space-y-4 text-sm text-navy-700">
            <div className="bg-white/60 rounded-xl p-4 border border-blue-100">
              <div className="font-bold text-primary flex items-center gap-1.5">
                <Package className="w-4 h-4" /> Véhicule neuf (VN)
              </div>
              <div className="mt-1 text-navy-600">Déposez le COC et la facture de vente.</div>
            </div>
            <div className="bg-white/60 rounded-xl p-4 border border-blue-100">
              <div className="font-bold text-purple-700 flex items-center gap-1.5">
                <Package className="w-4 h-4" /> Véhicule d'occasion (VO)
              </div>
              <div className="mt-1 text-navy-600">Déposez la carte grise barrée si vous l'avez. Vous verrez immédiatement si l'identification du véhicule est complète et conforme.</div>
              <div className="mt-2 text-primary text-xs">Si c'est le client qui la détient, cochez la case ci-dessous. Il pourra la déposer via le lien SMS, mais vous n'aurez la confirmation que lorsqu'il l'aura fait.</div>
              <div className="mt-2 text-navy-600 text-xs">Le certificat de cession sera généré automatiquement avec votre cachet et signature, et envoyé au client pour signature via le lien SMS.</div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-blue-200">
            <label className="flex items-start gap-2.5 cursor-pointer text-navy-700 hover:text-navy transition-colors">
              <input type="checkbox" className="mt-1 rounded border-blue-300 text-primary focus:ring-primary/20" onChange={async (e) => {
                if (e.target.checked) {
                  await fetch(`${API}/dossiers/${dossierId}/cg-chez-client`, { method: 'POST' })
                  reload()
                }
              }} />
              <span className="text-sm font-medium">Je n'ai pas la carte grise barrée — le client la déposera via le lien SMS</span>
            </label>
          </div>
          <div className="mt-3 pt-3 border-t border-blue-200 text-primary/70 text-xs">
            Les documents client (pièce d'identité, permis, justificatif de domicile) peuvent être déposés par vous ici ou par le client via un lien SMS.
          </div>
        </div>
      )}

      {/* Upload — fichier ou photo — adapté selon l'état */}
      {(dossier.status === 'PENDING' || dossier.status === 'ATTENTE_CLIENT') && !(checklist?.documents?.ok && checklist?.client_docs?.ready_for_diagnostic) && (
        <div className="border-2 border-dashed rounded-2xl p-8 text-center border-primary/30 bg-primary-light/20 mb-4 transition-all hover:border-primary/50 hover:bg-primary-light/30">
          <Upload className="w-8 h-8 mx-auto mb-2 text-primary/60" />
          <div className="font-semibold text-navy mb-1">
            {!checklist?.documents?.type_detecte
              ? 'Déposer un document'
              : checklist?.documents?.ok
                ? 'Déposer un document client'
                : 'Déposer un document'
            }
          </div>
          <p className="text-xs text-slate-500 mb-4">
            {!checklist?.documents?.type_detecte
              ? 'COC, facture, carte grise barrée, CNI, permis, justificatif de domicile...'
              : checklist?.documents?.ok
                ? 'CNI, permis, justificatif de domicile — ou envoyez un lien au client'
                : 'Document véhicule ou client — le système identifie automatiquement'
            }
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <input type="file" onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])}
              className="hidden" id="file-vendeur" accept="image/*,application/pdf" />
            <label htmlFor="file-vendeur"
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-xl text-sm font-medium cursor-pointer transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {uploading ? 'Analyse...' : 'Fichier'}
            </label>
            <ScanButton dossierId={dossierId} onUploaded={reload} />
          </div>
        </div>
      )}

      {/* Résultat dernier upload */}
      {lastUpload && lastUpload.quality && (
        <div className={`mb-4 p-4 rounded-2xl border ${
          lastUpload.quality.status === 'ok' ? 'bg-emerald-light/30 border-emerald/20' :
          lastUpload.quality.status === 'illisible' ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-200'
        }`}>
          <div className="flex items-center gap-2 font-medium text-sm mb-1">
            <span className="text-navy">{lastUpload.classification?.type || 'PENDING'}</span>
            <span>—</span>
            <QualityBadge status={lastUpload.quality.status} />
            {lastUpload.quality.ocr_confidence != null && (
              <span className="text-slate-400 text-xs ml-1">({(lastUpload.quality.ocr_confidence * 100).toFixed(0)}% {lastUpload.quality.ocr_provider})</span>
            )}
          </div>
          {lastUpload.quality.message && (
            <div className={`text-xs mt-1 ${lastUpload.quality.status === 'ok' ? 'text-emerald-dark' : 'text-red-600'}`}>
              {lastUpload.quality.message}
            </div>
          )}
          {lastUpload.extracted_fields && Object.keys(lastUpload.extracted_fields).length > 0 && (
            <div className="mt-2 text-xs text-slate-600 flex flex-wrap gap-x-4 gap-y-1">
              {Object.entries(lastUpload.extracted_fields).filter(([_, v]) => v).slice(0, 5).map(([k, v]) => (
                <span key={k}>{k}: <strong className="text-navy">{String(v)}</strong></span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Alerte CG non barrée */}
      {lastUpload?.cg_alerte?.cg_non_barree && (
        <div className="mb-4 p-4 rounded-2xl border bg-red-50 border-red-200 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-sm text-red-800 mb-1">Carte grise non barrée</div>
            <div className="text-xs text-red-700">{lastUpload.cg_alerte.message}</div>
          </div>
        </div>
      )}

      {/* Message de complétude */}
      {lastUpload?.completude && (
        <div className={`mb-4 p-4 rounded-2xl border flex items-start gap-3 ${
          lastUpload.completude.complet ? 'bg-emerald-light/30 border-emerald/30' : 'bg-amber-50 border-amber-200'
        }`}>
          {lastUpload.completude.complet
            ? <CheckCircle2 className="w-5 h-5 text-emerald flex-shrink-0 mt-0.5" />
            : <Info className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          }
          <div>
            <span className={`font-semibold text-sm ${lastUpload.completude.complet ? 'text-emerald-dark' : 'text-amber-800'}`}>
              {lastUpload.completude.message}
            </span>
            {lastUpload.completude.docs_manquants?.length > 0 && !lastUpload.completude.complet && (
              <div className="mt-2 flex flex-wrap gap-1">
                {lastUpload.completude.docs_manquants.map((d: string, i: number) => (
                  <span key={i} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">{d}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="space-y-3">
        {/* Docs véhicule OK — 3 cas selon l'état des docs client */}
        {checklist?.documents?.ok && checklist?.client_link_ready && dossier.status === 'PENDING' && (
          <>
            {/* Cas 1 : docs client avec alertes (CNI expirée, domicile ancien, nom divergent) */}
            {checklist?.client_docs?.alertes?.length > 0 ? (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-5 h-5 text-amber-500" />
                  <span className="text-amber-800 font-bold text-sm">Des corrections sont nécessaires</span>
                </div>
                <div className="ml-7 mb-3 space-y-1">
                  {checklist.client_docs.alertes.map((a: any, i: number) => (
                    <div key={i} className="flex items-start gap-1.5 text-sm text-navy-600">
                      <span className={a.type === 'erreur' ? 'text-red-400' : 'text-amber-400'}>—</span>
                      <span>{a.doc === 'CNI' || a.doc === 'PASSEPORT' ? 'Pièce d\'identité expirée' : a.doc === 'PERMIS' ? 'Permis expiré' : a.doc === 'DOMICILE' && a.message?.includes('correspond pas') ? 'Nom divergent — hébergement requis' : a.doc === 'DOMICILE' ? 'Justificatif de domicile de plus de 6 mois' : a.message?.slice(0, 60)}</span>
                    </div>
                  ))}
                  {checklist.client_docs.missing?.filter((m: any) => m.required).map((m: any, i: number) => (
                    <div key={`m-${i}`} className="flex items-start gap-1.5 text-sm text-navy-600">
                      <span className="text-red-400">—</span>
                      <span>{m.label} (manquant)</span>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-navy-600 mb-4 ml-7">Le client peut déposer les documents corrigés via un lien sécurisé.</p>
                <button onClick={confirmSendLink}
                  className="ml-7 inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
                  <Send className="w-4 h-4" />
                  Envoyer le lien par SMS
                </button>
              </div>
            ) : !checklist?.client_docs?.ready_for_diagnostic ? (
              /* Cas 2 : docs client manquants */
              <div className="bg-emerald-light/30 border border-emerald/20 rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald" />
                  <span className="text-emerald-dark font-bold text-sm">Documents véhicule vérifiés</span>
                </div>
                <p className="text-sm text-navy-600 mb-4 ml-7">Il manque les documents client. Vous pouvez les déposer vous-même ci-dessus, ou envoyer un lien au client pour qu'il les dépose.</p>
                <button onClick={confirmSendLink}
                  className="ml-7 inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
                  <Send className="w-4 h-4" />
                  Envoyer le lien par SMS
                </button>
              </div>
            ) : (
              /* Cas 3 : tout est prêt → envoyer le lien */
              <button onClick={confirmSendLink}
                className="w-full inline-flex items-center justify-center gap-2 bg-emerald hover:bg-emerald-dark text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
                <Send className="w-4 h-4" />
                Valider et envoyer le lien au client
              </button>
            )}
          </>
        )}
        {/* Docs véhicule pas encore OK → ancien message */}
        {checklist?.documents?.ok && !checklist?.client_link_ready && dossier.status === 'PENDING' && (
          <div className="bg-emerald-light/30 border border-emerald/20 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-5 h-5 text-emerald" />
              <span className="text-emerald-dark font-bold text-sm">Documents véhicule vérifiés</span>
            </div>
            <p className="text-sm text-navy-600 mb-4 ml-7">Il manque les documents client. Vous pouvez les déposer vous-même ci-dessus, ou envoyer un lien au client pour qu'il les dépose.</p>
            <button onClick={confirmSendLink}
              className="ml-7 inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
              <Send className="w-4 h-4" />
              Envoyer le lien par SMS
            </button>
          </div>
        )}
        {dossier.status === 'ATTENTE_CLIENT' && (
          <div className="text-center py-4 text-slate-500 text-sm bg-amber-50 border border-amber-200 rounded-2xl flex items-center justify-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            En attente des documents du client. Vous serez notifié dès qu'il avance. Vous pouvez aussi déposer les documents manquants ci-dessus.
          </div>
        )}
        {dossier.diagnostic === 'VERT' && (
          <>
            <button onClick={() => window.open(`${API}/dossiers/${dossierId}/cerfa`, '_blank')}
              className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
              <Download className="w-4 h-4" />
              Télécharger le Cerfa
            </button>
            {/* CNIT après génération — si pas encore saisi */}
            {checklist?.documents?.items?.some((d: any) => d.has_cnit === false) && (
              <div className="mt-3">
                <div className="p-3 bg-primary-light/50 border border-blue-200 rounded-xl text-xs text-primary mb-2 flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  Le CNIT n'est pas inclus dans le Cerfa (COC européen). Saisissez-le ci-dessous pour re-générer le Cerfa avec le CNIT, ou saisissez-le directement dans le SIV.
                </div>
                <CnitInput dossierId={dossierId} onSaved={reload} />
              </div>
            )}
          </>
        )}
        {dossier.diagnostic === 'ROUGE' && (
          <div className="text-center text-sm text-red-600 py-4 bg-red-50 border border-red-200 rounded-2xl flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Des corrections sont nécessaires avant de générer le Cerfa
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

  if (!admin) return (
    <div className="text-center py-20 text-slate-400">
      <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin text-primary" />
      <p className="text-sm">Chargement...</p>
    </div>
  )

  const dossierName = [
    admin.client_nom || 'INCONNU',
    admin.type || 'XX',
    admin.reference,
    admin.vin || admin.immatriculation || '',
  ].filter(Boolean).join('_')

  return (
    <div>
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-primary hover:text-primary-dark text-sm font-medium mb-5 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Retour au tableau de bord
      </button>
      <h2 className="text-xl font-extrabold text-navy tracking-tight mb-1">Dossier complet</h2>
      <p className="text-slate-500 text-sm mb-6 font-mono bg-slate-100 inline-block px-3 py-1 rounded-lg">{dossierName}</p>

      {/* Infos */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 mb-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-slate-500">Titulaire :</span> <strong className="text-navy">{admin.client_nom} {admin.client_prenom}</strong></div>
          <div><span className="text-slate-500">Type :</span> <strong className="text-navy">{admin.type}</strong></div>
          <div><span className="text-slate-500">Référence :</span> <strong className="text-navy">{admin.reference}</strong></div>
          <div><span className="text-slate-500">VIN :</span> <span className="font-mono text-navy">{admin.vin || '—'}</span></div>
          <div><span className="text-slate-500">Immatriculation :</span> <span className="font-mono text-navy">{admin.immatriculation || '—'}</span></div>
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Cerfa :</span>
            {admin.cerfa_genere
              ? <span className="inline-flex items-center gap-1 text-emerald font-semibold"><CheckCircle2 className="w-4 h-4" /> Généré</span>
              : <span className="text-slate-400">—</span>
            }
          </div>
        </div>
      </div>

      {/* Documents vendeur */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm mb-4 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 bg-primary-light/50 text-sm font-semibold text-primary flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Documents vendeur ({admin.documents_vendeur?.length || 0})
        </div>
        {(admin.documents_vendeur || []).map((doc: any) => (
          <div key={doc.id} className="px-5 py-3 border-b last:border-0 flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" />
              <span className="font-medium text-navy">{doc.type}</span>
              <span className="text-slate-400 text-xs">{doc.filename}</span>
            </div>
            <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium border ${
              doc.status === 'EXTRACTED' ? 'bg-emerald-light text-emerald-dark border-emerald/20' : 'bg-slate-100 text-slate-500 border-slate-200'
            }`}>
              {doc.status === 'EXTRACTED' && <CheckCircle2 className="w-3 h-3" />}
              {doc.status}
            </span>
          </div>
        ))}
      </div>

      {/* Documents client */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm mb-4 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 bg-emerald-light/50 text-sm font-semibold text-emerald flex items-center gap-2">
          <User className="w-4 h-4" />
          Documents client ({admin.documents_client?.length || 0})
        </div>
        {(admin.documents_client || []).map((doc: any) => (
          <div key={doc.id} className="px-5 py-3 border-b last:border-0 flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" />
              <span className="font-medium text-navy">{doc.type}</span>
              <span className="text-slate-400 text-xs">{doc.filename}</span>
            </div>
            <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-medium border ${
              doc.status === 'EXTRACTED' ? 'bg-emerald-light text-emerald-dark border-emerald/20' : 'bg-slate-100 text-slate-500 border-slate-200'
            }`}>
              {doc.status === 'EXTRACTED' && <CheckCircle2 className="w-3 h-3" />}
              {doc.status}
            </span>
          </div>
        ))}
        {(!admin.documents_client || admin.documents_client.length === 0) && (
          <div className="px-5 py-4 text-sm text-slate-400 flex items-center gap-2">
            <Circle className="w-4 h-4" /> Aucun document client
          </div>
        )}
      </div>

      {/* Cerfa généré */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm mb-4 overflow-hidden">
        <div className="px-5 py-3.5 border-b bg-navy text-sm font-semibold text-white flex items-center gap-2">
          <Stamp className="w-4 h-4" />
          Cerfa généré
        </div>
        {admin.cerfa_genere ? (
          <div className="px-5 py-4 flex items-center justify-between">
            <div className="text-sm flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald" />
              <span className="font-medium text-navy">Cerfa {admin.type === 'VN' ? '13749' : '13750'}</span>
              <span className="text-slate-400">Cachet + signature apposés automatiquement</span>
            </div>
            <button onClick={() => window.open(`${API}/dossiers/${dossierId}/cerfa`, '_blank')}
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-xl text-sm font-medium transition-all">
              <Download className="w-4 h-4" /> Télécharger
            </button>
          </div>
        ) : (
          <div className="px-5 py-4 text-sm text-slate-400 flex items-center gap-2">
            <Circle className="w-4 h-4" /> Cerfa non encore généré
          </div>
        )}
      </div>

      {/* Télécharger tout */}
      {admin.cerfa_genere && (
        <button onClick={() => window.open(`${API}/dossiers/${dossierId}/download-zip`, '_blank')}
          className="w-full inline-flex items-center justify-center gap-2 bg-navy hover:bg-navy-800 text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg">
          <Archive className="w-4 h-4" />
          Télécharger le dossier complet (ZIP)
        </button>
      )}
    </div>
  )
}

// ─── 3. FACTURATION ─────────────────────────────────────────────────────────

function Facturation() {
  const [dossiers, setDossiers] = useState<Dossier[]>([])

  useEffect(() => {
    fetch(`${API}/dossiers/?professionnel_id=${getProId()}`).then(r => r.json()).then(setDossiers).catch(() => {})
  }, [])

  const traites = dossiers.filter(d => d.status === 'CERFA_GENERE')
  const enCours = dossiers.filter(d => d.status !== 'CERFA_GENERE' && d.status !== 'CLOSED')
  const montantDu = traites.length * 12 // TODO: 12 moto / 14 voiture
  const verrou = enCours.length >= 5

  return (
    <div>
      <h1 className="text-2xl font-extrabold text-navy tracking-tight mb-8">Facturation</h1>

      {/* Dossiers à régler */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-5">
          <CreditCard className="w-5 h-5 text-primary" />
          Dossiers à régler
        </h2>
        <div className="grid grid-cols-3 gap-4 mb-5">
          <div className="text-center p-5 bg-primary-light/50 rounded-2xl border border-blue-100">
            <div className="text-3xl font-extrabold text-primary tracking-tight">{enCours.length}/5</div>
            <div className="text-sm text-primary/70 font-medium mt-1">Dossiers en cours</div>
          </div>
          <div className="text-center p-5 bg-slate-50 rounded-2xl border border-slate-100">
            <div className="text-3xl font-extrabold text-navy tracking-tight">{traites.length}</div>
            <div className="text-sm text-slate-500 font-medium mt-1">Dossiers traités</div>
          </div>
          <div className="text-center p-5 bg-orange-50 rounded-2xl border border-orange-100">
            <div className="text-3xl font-extrabold text-orange-600 tracking-tight">{montantDu} EUR</div>
            <div className="text-sm text-orange-600/70 font-medium mt-1">Montant dû</div>
          </div>
        </div>
        {verrou && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 mb-4 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            Réglez vos dossiers en cours pour pouvoir en créer de nouveaux.
          </div>
        )}
        {montantDu > 0 && (
          <button className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
            <CreditCard className="w-4 h-4" />
            Payer {montantDu} EUR
          </button>
        )}
      </div>

      {/* Mes factures */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-4">
          <FileText className="w-5 h-5 text-primary" />
          Mes factures
        </h2>
        <div className="text-center py-10 text-slate-400 text-sm">
          <FileText className="w-10 h-10 mx-auto mb-2 text-slate-300" />
          Aucune facture pour le moment
        </div>
      </div>

      {/* Export */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-4">
          <Download className="w-5 h-5 text-primary" />
          Export comptable
        </h2>
        <div className="flex gap-3">
          <button className="inline-flex items-center gap-2 px-4 py-2.5 border border-slate-200 rounded-xl text-sm text-navy-700 font-medium hover:bg-slate-50 hover:border-slate-300 transition-all">
            <Download className="w-4 h-4 text-slate-400" />
            Télécharger CSV
          </button>
          <button className="inline-flex items-center gap-2 px-4 py-2.5 border border-slate-200 rounded-xl text-sm text-navy-700 font-medium hover:bg-slate-50 hover:border-slate-300 transition-all">
            <Download className="w-4 h-4 text-slate-400" />
            Télécharger PDF
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── 4. PARAMÈTRES ──────────────────────────────────────────────────────────

function ProfilCommerce({ profil, onUpdate }: { profil: any; onUpdate: (p: any) => void }) {
  const [editingContact, setEditingContact] = useState(false)
  const [tel, setTel] = useState(profil.telephone_commerce || '')
  const [email, setEmail] = useState(profil.email_commerce || '')
  const [saving, setSaving] = useState(false)

  const saveContact = async () => {
    setSaving(true)
    await fetch(`${API}/professionnel/profil?pro_id=${getProId()}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nom_commerce: profil.nom_commerce, adresse: profil.adresse,
        telephone_commerce: tel, email_commerce: email || null,
        assurance_flotte_vn: profil.assurance_flotte_vn, assurance_flotte_vo: profil.assurance_flotte_vo,
        demander_assurance_client_vn: profil.demander_assurance_client_vn,
        demander_assurance_client_vo: profil.demander_assurance_client_vo,
      }),
    })
    const updated = await fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json())
    onUpdate(updated)
    setSaving(false); setEditingContact(false)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
      <h2 className="flex items-center gap-2 font-bold text-navy mb-2">
        <Building2 className="w-5 h-5 text-primary" />
        Profil commerce
      </h2>
      <p className="text-xs text-slate-400 mb-5 ml-7">Ces infos apparaîtront dans le SMS reçu par vos clients pour qu'ils sachent qui les contacte.</p>

      {/* Infos extraites du Kbis — non modifiables */}
      <div className="p-4 bg-slate-50 rounded-xl mb-5 border border-slate-100">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Extraits automatiquement du Kbis</div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-slate-500">Nom commerce :</span> <strong className="text-navy">{profil.nom_commerce || '—'}</strong></div>
          <div><span className="text-slate-500">Adresse :</span> <strong className="text-navy">{profil.adresse || '—'}</strong></div>
          <div><span className="text-slate-500">SIRET :</span> <strong className="text-navy">{profil.siret || '—'}</strong></div>
          <div><span className="text-slate-500">Raison sociale :</span> <strong className="text-navy">{profil.raison_sociale || '—'}</strong></div>
        </div>
        <p className="text-xs text-primary mt-3 flex items-center gap-1">
          <Info className="w-3 h-3" />
          Pour modifier ces informations, déposez un Kbis mis à jour dans la section Documents ci-dessous.
        </p>
      </div>

      {/* Contact — modifiable */}
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Coordonnées de contact (modifiables)</div>
      {editingContact ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-navy-600 mb-1.5">Téléphone *</label>
              <input value={tel} onChange={e => setTel(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy-600 mb-1.5">Email</label>
              <input value={email} onChange={e => setEmail(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={saveContact} disabled={saving}
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50 transition-all">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
            <button onClick={() => setEditingContact(false)}
              className="text-slate-500 hover:text-navy px-4 py-2 text-sm font-medium transition-colors">
              Annuler
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <div className="grid grid-cols-2 gap-4 text-sm flex-1">
            <div className="flex items-center gap-2"><Phone className="w-3.5 h-3.5 text-slate-400" /><span className="text-slate-500">Téléphone :</span> <span className="text-navy">{profil.telephone_commerce || '—'}</span></div>
            <div className="flex items-center gap-2"><Mail className="w-3.5 h-3.5 text-slate-400" /><span className="text-slate-500">Email :</span> <span className="text-navy">{profil.email_commerce || '—'}</span></div>
          </div>
          <button onClick={() => setEditingContact(true)}
            className="inline-flex items-center gap-1.5 text-primary hover:text-primary-dark text-sm font-medium ml-4 transition-colors">
            <Pencil className="w-3.5 h-3.5" /> Modifier
          </button>
        </div>
      )}
    </div>
  )
}

function AgentHabiliteForm({ profil, onUpdate }: { profil: any; onUpdate: (p: any) => void }) {
  const [agentNom, setAgentNom] = useState(profil.agent_nom || '')
  const [agentSiret, setAgentSiret] = useState(profil.agent_siret || '')
  const [agentHabilitation, setAgentHabilitation] = useState(profil.agent_numero_habilitation || '')
  const [agentTel, setAgentTel] = useState(profil.agent_telephone || '')
  const [agentEmail, setAgentEmail] = useState(profil.agent_email || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    await fetch(`${API}/professionnel/profil?pro_id=${getProId()}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nom_commerce: profil.nom_commerce, adresse: profil.adresse,
        telephone_commerce: profil.telephone_commerce, email_commerce: profil.email_commerce,
        type_compte: profil.type_compte,
        assurance_flotte_vn: profil.assurance_flotte_vn, assurance_flotte_vo: profil.assurance_flotte_vo,
        demander_assurance_client_vn: profil.demander_assurance_client_vn,
        demander_assurance_client_vo: profil.demander_assurance_client_vo,
        agent_nom: agentNom || null, agent_siret: agentSiret || null,
        agent_numero_habilitation: agentHabilitation || null,
        agent_telephone: agentTel || null, agent_email: agentEmail || null,
      }),
    })
    const updated = await fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json())
    onUpdate(updated)
    setSaving(false)
  }

  const hasAgent = agentNom && agentSiret && agentHabilitation

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
      <h2 className="flex items-center gap-2 font-bold text-navy mb-2">
        <User className="w-5 h-5 text-primary" />
        Agent habilité SIV
      </h2>
      <p className="text-xs text-slate-400 mb-5 ml-7">Renseignez les coordonnées de l'agent habilité qui soumettra vos dossiers au SIV. Son numéro d'habilitation sera inscrit sur le Cerfa.</p>

      <div className="space-y-3 ml-7">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Nom de l'agent / structure *</label>
            <input value={agentNom} onChange={e => setAgentNom(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="Garage Martin CG" />
          </div>
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">SIRET *</label>
            <input value={agentSiret} onChange={e => setAgentSiret(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm font-mono bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="123 456 789 00012" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-navy-600 mb-1.5">Numéro d'habilitation SIV *</label>
          <input value={agentHabilitation} onChange={e => setAgentHabilitation(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm font-mono bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            placeholder="H-75-2024-00123" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Téléphone</label>
            <input value={agentTel} onChange={e => setAgentTel(e.target.value)} type="tel"
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="01 23 45 67 89" />
          </div>
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Email</label>
            <input value={agentEmail} onChange={e => setAgentEmail(e.target.value)} type="email"
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="agent@exemple.fr" />
          </div>
        </div>
        <div className="flex items-center gap-3 pt-2">
          <button onClick={save} disabled={saving}
            className="inline-flex items-center gap-2 bg-primary hover:bg-primary-dark text-white px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50 transition-all">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            {saving ? 'Enregistrement...' : 'Enregistrer'}
          </button>
          {hasAgent && (
            <span className="inline-flex items-center gap-1 text-xs text-emerald font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> Agent renseigné
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function Parametres() {
  const [profil, setProfil] = useState<any>(null)

  useEffect(() => {
    fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json()).then(setProfil).catch(() => {})
  }, [])

  if (!profil) return (
    <div className="text-center py-20 text-slate-400">
      <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin text-primary" />
      <p className="text-sm">Chargement...</p>
    </div>
  )

  return (
    <div>
      <h1 className="text-2xl font-extrabold text-navy tracking-tight mb-2">Paramètres</h1>
      <p className="text-slate-500 mb-8">Configurez votre espace. Ces informations seront utilisées pour communiquer avec vos clients.</p>

      {/* Type de compte */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-2">
          <ShieldCheck className="w-5 h-5 text-primary" />
          Type de compte
        </h2>
        <p className="text-xs text-slate-400 mb-4 ml-7">Ce choix adapte le fonctionnement du système à votre activité.</p>
        <div className="space-y-2 ml-7">
          {[
            { id: 'VENDEUR_HABILITE', label: 'Vendeur habilité SIV', desc: 'Vous vendez des véhicules et soumettez au SIV vous-même.' },
            { id: 'VENDEUR_NON_HABILITE', label: 'Vendeur non habilité', desc: 'Vous vendez des véhicules et votre agent habilité soumet au SIV.' },
            { id: 'AGENT_HABILITE', label: 'Agent habilité SIV', desc: 'Vous traitez les cartes grises pour le compte de vos clients.' },
          ].map(opt => (
            <label key={opt.id}
              className={`flex items-start gap-3 p-3.5 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
                profil.type_compte === opt.id
                  ? 'border-primary bg-primary-light/30 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300'
              }`}>
              <input type="radio" name="type_compte" value={opt.id}
                checked={profil.type_compte === opt.id}
                onChange={async () => {
                  setProfil({ ...profil, type_compte: opt.id })
                  await fetch(`${API}/professionnel/profil/type-compte?pro_id=${getProId()}`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type_compte: opt.id }),
                  })
                  fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json()).then(setProfil)
                }}
                className="mt-1 text-primary focus:ring-primary/20" />
              <div>
                <div className={`text-sm font-semibold ${profil.type_compte === opt.id ? 'text-primary' : 'text-navy'}`}>{opt.label}</div>
                <div className="text-xs text-slate-500">{opt.desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Agent habilité (vendeur non habilité uniquement) */}
      {profil.type_compte === 'VENDEUR_NON_HABILITE' && (
        <AgentHabiliteForm profil={profil} onUpdate={setProfil} />
      )}

      <ProfilCommerce profil={profil} onUpdate={setProfil} />

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-2">
          <Stamp className="w-5 h-5 text-primary" />
          Documents obligatoires
        </h2>
        <p className="text-xs text-slate-400 mb-5 ml-7">Votre cachet et signature seront apposés automatiquement sur tous les documents (Cerfa, facture, cession). Le Kbis identifie votre structure.</p>
        <div className="space-y-3 text-sm">
          {[
            { key: 'cachet', label: 'Cachet commercial', uploaded: profil.cachet_uploaded, endpoint: 'cachet', desc: 'Photo de votre cachet sur fond blanc', icon: <Stamp className="w-4 h-4" /> },
            { key: 'signature', label: 'Signature', uploaded: profil.signature_uploaded, endpoint: 'signature', desc: 'Photo de votre signature sur fond blanc', icon: <PenTool className="w-4 h-4" /> },
            { key: 'kbis', label: 'Kbis', uploaded: profil.kbis_uploaded, endpoint: 'kbis', desc: 'Kbis de moins de 3 mois — SIREN et raison sociale extraits automatiquement', icon: <FileText className="w-4 h-4" /> },
          ].map(doc => (
            <div key={doc.key} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-200 transition-all">
              <div className="flex items-center gap-3">
                {doc.uploaded
                  ? <div className="w-8 h-8 rounded-lg bg-emerald-light flex items-center justify-center"><CheckCircle2 className="w-4 h-4 text-emerald" /></div>
                  : <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center"><XCircle className="w-4 h-4 text-red-400" /></div>
                }
                <div>
                  <div className="font-semibold text-navy">{doc.label}</div>
                  <div className="text-xs text-slate-400">{doc.desc}</div>
                </div>
              </div>
              <div>
                <input type="file" className="hidden" id={`upload-${doc.key}`}
                  accept="image/*,application/pdf"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    const form = new FormData(); form.append('file', file)
                    await fetch(`${API}/professionnel/profil/${doc.endpoint}?pro_id=${getProId()}`, { method: 'POST', body: form })
                    // Recharger le profil
                    fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json()).then(setProfil)
                  }} />
                <label htmlFor={`upload-${doc.key}`}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all ${
                    doc.uploaded
                      ? 'bg-primary/10 text-primary hover:bg-primary/20'
                      : 'bg-emerald text-white hover:bg-emerald-dark'
                  }`}>
                  {doc.uploaded ? <><Pencil className="w-3 h-3" /> Modifier</> : <><Upload className="w-3 h-3" /> Déposer</>}
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h2 className="flex items-center gap-2 font-bold text-navy mb-4">
          <ShieldCheck className="w-5 h-5 text-primary" />
          Assurance flotte
        </h2>
        <p className="text-sm text-slate-500 mb-5 ml-7">
          Votre assurance flotte couvre-t-elle les véhicules vendus en attendant la finalisation au SIV ?
          Cette info nous permet d'adapter la demande d'attestation d'assurance auprès de vos clients.
        </p>
        <div className="space-y-4 text-sm">
          {/* VN */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
            <div className="flex items-center gap-2.5 mb-1">
              {profil.assurance_flotte_vn
                ? <div className="w-6 h-6 rounded-full bg-emerald-light flex items-center justify-center"><Check className="w-3.5 h-3.5 text-emerald" /></div>
                : <div className="w-6 h-6 rounded-full bg-red-50 flex items-center justify-center"><X className="w-3.5 h-3.5 text-red-400" /></div>
              }
              <strong className="text-navy">Véhicules neufs (VN)</strong>
              <span className="text-slate-400">— {profil.assurance_flotte_vn ? 'couvert par la flotte' : 'non couvert'}</span>
            </div>
            {!profil.assurance_flotte_vn && (
              <div className="ml-8 text-slate-500">
                Demander l'attestation au client : {profil.demander_assurance_client_vn
                  ? <span className="text-primary font-semibold">oui, automatiquement</span>
                  : <span className="text-slate-400">non, vous gérez directement</span>}
              </div>
            )}
          </div>
          {/* VO */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
            <div className="flex items-center gap-2.5 mb-1">
              {profil.assurance_flotte_vo
                ? <div className="w-6 h-6 rounded-full bg-emerald-light flex items-center justify-center"><Check className="w-3.5 h-3.5 text-emerald" /></div>
                : <div className="w-6 h-6 rounded-full bg-red-50 flex items-center justify-center"><X className="w-3.5 h-3.5 text-red-400" /></div>
              }
              <strong className="text-navy">Véhicules d'occasion (VO)</strong>
              <span className="text-slate-400">— {profil.assurance_flotte_vo ? 'couvert par la flotte' : 'non couvert'}</span>
            </div>
            {!profil.assurance_flotte_vo && (
              <div className="ml-8 text-slate-500">
                Demander l'attestation au client : {profil.demander_assurance_client_vo
                  ? <span className="text-primary font-semibold">oui, automatiquement</span>
                  : <span className="text-slate-400">non, vous gérez directement</span>}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Page publique (URL permanente) */}
      <PagePubliqueConfig profil={profil} onUpdate={setProfil} />
    </div>
  )
}


function PagePubliqueConfig({ profil, onUpdate }: { profil: any; onUpdate: (p: any) => void }) {
  const [slug, setSlug] = useState(profil.slug || '')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const currentUrl = profil.page_publique_url || (profil.slug ? `https://app.autodocpro.fr/public/${profil.slug}` : null)

  const saveSlug = async () => {
    if (!slug.trim()) return
    setSaving(true); setMsg(null)
    const res = await fetch(`${API}/professionnel/profil/page-publique?pro_id=${getProId()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug: slug.trim() }),
    })
    const data = await res.json()
    setSaving(false)
    if (res.ok) {
      setMsg({ text: `Page activée : ${data.url}`, ok: true })
      setSlug(data.slug)
      fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json()).then(onUpdate)
    } else {
      setMsg({ text: data.detail || 'Erreur', ok: false })
    }
  }

  const disable = async () => {
    await fetch(`${API}/professionnel/profil/page-publique?pro_id=${getProId()}`, { method: 'DELETE' })
    setMsg({ text: 'Page publique désactivée.', ok: true })
    fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => r.json()).then(onUpdate)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mt-6">
      <h2 className="flex items-center gap-2 font-bold text-navy mb-2">
        <CircleDot className="w-5 h-5 text-primary" />
        Page publique (URL permanente)
      </h2>
      <p className="text-xs text-slate-400 mb-5 ml-7">
        Créez un lien permanent que vos clients peuvent utiliser pour déposer leurs documents directement.
        Idéal pour votre site web, cartes de visite ou affichage en boutique.
      </p>

      <div className="ml-7 space-y-4">
        {/* Slug input */}
        <div>
          <label className="block text-xs font-medium text-navy-600 mb-1.5">
            Adresse de votre page
          </label>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 whitespace-nowrap">.../public/</span>
            <input
              value={slug}
              onChange={e => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
              className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="dupont-motos-lyon"
            />
            <button onClick={saveSlug} disabled={saving || !slug.trim()}
              className="inline-flex items-center gap-1.5 bg-emerald hover:bg-emerald-dark text-white px-4 py-2 rounded-xl text-xs font-medium disabled:opacity-50 transition-all">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
              {profil.page_publique_active ? 'Modifier' : 'Activer'}
            </button>
          </div>
        </div>

        {/* Status + QR code */}
        {profil.page_publique_active && currentUrl && (
          <div className="bg-emerald-light/30 border border-emerald/20 rounded-xl p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald" />
                  <span className="text-sm font-semibold text-navy">Page active</span>
                </div>
                <a href={currentUrl} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline break-all">
                  {currentUrl}
                </a>
                <div className="mt-3">
                  <button onClick={disable}
                    className="text-xs text-red-500 hover:text-red-700 transition-colors">
                    Désactiver la page
                  </button>
                </div>
              </div>
              <div className="flex-shrink-0 bg-white rounded-xl p-2 border border-slate-200 shadow-sm">
                <QRCodeSVG value={currentUrl} size={96} />
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-3">
              Scannez ce QR code ou partagez le lien pour que vos clients déposent leurs documents.
            </p>
          </div>
        )}

        {!profil.page_publique_active && profil.slug && (
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-500 flex items-center gap-2">
            <Info className="w-4 h-4 text-slate-400" />
            Page actuellement désactivée. Cliquez sur "Activer" pour la remettre en ligne.
          </div>
        )}

        {/* Feedback */}
        {msg && (
          <div className={`p-3 rounded-xl text-xs flex items-center gap-2 ${
            msg.ok ? 'bg-emerald-light/50 text-emerald-dark border border-emerald/20' : 'bg-red-50 text-red-600 border border-red-200'
          }`}>
            {msg.ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            {msg.text}
          </div>
        )}
      </div>
    </div>
  )
}


// ─── MAIN APP ───────────────────────────────────────────────────────────────

export default function App() {
  if (MAINTENANCE) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center px-6">
          <Settings className="w-16 h-16 text-slate-400 mx-auto mb-4 animate-spin" style={{ animationDuration: '3s' }} />
          <h1 className="text-2xl font-bold text-slate-800 mb-2">Maintenance en cours</h1>
          <p className="text-slate-500 max-w-md">
            AutoDoc Pro est en cours de maintenance. Nous serons de retour très bientôt.
          </p>
        </div>
      </div>
    )
  }

  const path = window.location.pathname

  // Page client (lien SMS) : /client/{token}
  const clientMatch = path.match(/\/client\/(.+)/)
  if (clientMatch) {
    return <ClientPage token={clientMatch[1]} />
  }

  // Page client public (URL permanente) : /public/{slug}
  const publicMatch = path.match(/\/public\/(.+)/)
  if (publicMatch) {
    return <PublicClientPage slug={publicMatch[1]} />
  }

  // Démos interactives
  if (path === '/demo') return <DemoPage mode="vendeur_habilite" />
  if (path === '/demo-vendeur') return <DemoPage mode="vendeur_non_habilite" />
  if (path === '/demo-agent') return <DemoPage mode="agent_habilite" />

  return <ProApp />
}

function DemoPage({ mode }: { mode: 'vendeur_habilite' | 'vendeur_non_habilite' | 'agent_habilite' }) {
  const configs = {
    vendeur_habilite: {
      badge: 'Vendeur habilité',
      ref: 'CG-2026-DEMO',
      type: 'VO',
      client: 'DUPONT Marie',
      vin: 'UDUE•••••••08739',
      vehiculeDocs: [
        { label: 'CG barrée', detail: 'cg_dupont.pdf', badges: ['dép. pro'] },
        { label: 'Certificat de cession', detail: 'cession_signee.pdf', badges: ['dép. pro', 'sig. client'] },
      ],
      identiteDocs: [
        { label: 'CNI', detail: 'recto + verso', badges: ['dép. client'] },
        { label: 'Permis', detail: 'cat. A2', badges: ['dép. client'] },
        { label: 'Domicile', detail: 'quittance EDF', badges: ['dép. client'] },
      ],
      mandats: null,
      message: 'Nickel, tous les documents sont là ! Le Cerfa est prêt — téléchargez-le et soumettez au SIV.',
      backUrl: '/',
    },
    vendeur_non_habilite: {
      badge: 'Vendeur non habilité',
      ref: 'CG-2026-DEMO-V',
      type: 'VN',
      client: 'MARTIN Jean',
      vin: 'JMZKECW••••12345',
      vehiculeDocs: [
        { label: 'COC', detail: 'Honda CB125R — 11 kW', badges: ['dép. pro'] },
        { label: 'Facture', detail: 'facture_honda.pdf', badges: ['dép. pro'] },
      ],
      identiteDocs: [
        { label: 'CNI', detail: 'recto + verso', badges: ['dép. client'] },
        { label: 'Permis', detail: 'cat. B — obtenu 12/03/2022', badges: ['dép. client'] },
        { label: 'Domicile', detail: 'quittance EDF', badges: ['dép. client'] },
        { label: 'Formation 7h', detail: 'détectée — permis B + 125cc', badges: ['dép. client'] },
      ],
      mandats: [
        { label: 'Mandat client → vendeur', detail: '13757', badges: ['dép. pro', 'sig. client'] },
        { label: 'Mandat client → agent', detail: '13757 — Garage Central SIV', badges: ['dép. pro', 'sig. client', 'sig. agent'] },
      ],
      message: 'Dossier prêt ! Transmettez-le à Garage Central SIV pour soumission au SIV.',
      backUrl: '/vendeur.html',
    },
    agent_habilite: {
      badge: 'Agent habilité',
      ref: 'CG-2026-DEMO-A',
      type: 'VO',
      client: 'LECLERC Sophie',
      vin: 'VF3LC••••••67890',
      vehiculeDocs: [
        { label: 'CG barrée', detail: 'AB-123-CD', badges: ['dép. client'] },
        { label: 'Cession 15776', detail: 'signée', badges: ['dép. client'] },
      ],
      identiteDocs: [
        { label: 'CNI', detail: 'recto + verso', badges: ['dép. client'] },
        { label: 'Permis', detail: 'cat. B', badges: ['dép. client'] },
        { label: 'Domicile', detail: 'quittance Engie', badges: ['dép. client'] },
        { label: 'Attestation hébergement', detail: 'détectée auto', badges: ['dép. client'] },
        { label: 'CNI hébergeant', detail: 'recto + verso', badges: ['dép. client'] },
      ],
      mandats: null,
      message: 'Tous les documents sont vérifiés. Hébergement détecté et validé. Cerfa prêt — soumettez au SIV.',
      backUrl: '/agent.html',
    },
  }

  const c = configs[mode]
  const badgeColors: Record<string, string> = {
    'dép. pro': 'bg-primary-light text-primary border-blue-200',
    'dép. client': 'bg-amber-50 text-amber-600 border-amber-200',
    'sig. client': 'bg-amber-50 text-amber-600 border-amber-200',
    'sig. agent': 'bg-purple-50 text-purple-600 border-purple-200',
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="sticky top-0 z-50 bg-white/92 backdrop-blur-xl border-b border-slate-200/80 shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-16">
          <a href="/" className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-emerald flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
            </span>
            <span className="text-lg font-extrabold text-navy tracking-tight">AutoDoc Pro</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">Démo — {c.badge}</span>
          </a>
          <a href={c.backUrl} className="text-sm text-primary font-medium hover:text-primary-dark transition-colors">
            ← Retour au site
          </a>
        </div>
      </nav>
      <div className="max-w-6xl mx-auto px-6 py-8 pb-16">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6 flex items-center gap-3">
          <Info className="w-5 h-5 text-amber-500 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-800">Mode démonstration — {c.badge}</p>
            <p className="text-xs text-amber-700">Ce dossier est pré-rempli avec des données fictives. Explorez l'interface pour voir comment AutoDoc Pro fonctionne.</p>
          </div>
        </div>

        {/* En-tête */}
        <div className="flex items-center justify-between mb-6 bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <div>
            <h2 className="text-xl font-extrabold text-navy tracking-tight">{c.ref}</h2>
            <p className="text-slate-500 text-sm mt-1 flex items-center gap-2 flex-wrap">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${c.type === 'VN' ? 'bg-primary-light text-primary border-blue-200' : 'bg-purple-50 text-purple-700 border-purple-200'}`}>
                <Package className="w-3 h-3" />{c.type}
              </span>
              <span className="text-navy-700">{c.client}</span>
              <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">{c.vin}</span>
              {mode === 'agent_habilite' && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200 font-medium">Client public</span>}
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-emerald-light text-emerald border-emerald/20">
            <CheckCircle2 className="w-3 h-3" />Complet
          </span>
        </div>

        {/* Checklist */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 mb-4">
          <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
            <FileCheck className="w-4 h-4 text-primary" />Checklist
          </h3>

          <div className="mb-4">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
              <span>Véhicule</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-light text-emerald rounded-full text-xs font-semibold border border-emerald/20"><Lock className="w-3 h-3" /> Verrouillé</span>
            </div>
            {c.vehiculeDocs.map((item, i) => (
              <div key={i} className="flex items-center gap-2.5 text-sm py-1.5 flex-wrap">
                <CheckCircle2 className="w-4 h-4 text-emerald flex-shrink-0" />
                <span className="text-navy-700">{item.label}</span>
                <span className="text-slate-400 text-xs">— {item.detail}</span>
                {item.badges.map((b, j) => <span key={j} className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${badgeColors[b] || ''}`}>{b}</span>)}
              </div>
            ))}
          </div>

          <div className="mb-4">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
              <span>Identité client</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-light text-emerald rounded-full text-xs font-semibold border border-emerald/20"><Lock className="w-3 h-3" /> Verrouillé</span>
            </div>
            {c.identiteDocs.map((item, i) => (
              <div key={i} className="flex items-center gap-2.5 text-sm py-1.5 flex-wrap">
                <CheckCircle2 className="w-4 h-4 text-emerald flex-shrink-0" />
                <span className="text-navy-700">{item.label}</span>
                <span className="text-slate-400 text-xs">— {item.detail}</span>
                {item.badges.map((b, j) => <span key={j} className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${badgeColors[b] || ''}`}>{b}</span>)}
              </div>
            ))}
          </div>

          {c.mandats && (
            <div className="mb-4">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <span>Mandats</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-light text-emerald rounded-full text-xs font-semibold border border-emerald/20"><CheckCircle2 className="w-3 h-3" /> Signés</span>
              </div>
              {c.mandats.map((item, i) => (
                <div key={i} className="flex items-center gap-2.5 text-sm py-1.5 flex-wrap">
                  <CheckCircle2 className="w-4 h-4 text-emerald flex-shrink-0" />
                  <span className="text-navy-700">{item.label}</span>
                  <span className="text-slate-400 text-xs">— {item.detail}</span>
                  {item.badges.map((b, j) => <span key={j} className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${badgeColors[b] || ''}`}>{b}</span>)}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mb-4 p-4 rounded-2xl border flex items-start gap-3 bg-emerald-light/30 border-emerald/30">
          <CheckCircle2 className="w-5 h-5 text-emerald flex-shrink-0 mt-0.5" />
          <span className="font-semibold text-sm text-emerald-dark">{c.message}</span>
        </div>

        <button className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-primary/20 mb-3"
          onClick={() => alert('Démo : dans la version réelle, le Cerfa PDF est téléchargé ici.')}>
          <Download className="w-4 h-4" />Télécharger le Cerfa
        </button>
        <button className="w-full inline-flex items-center justify-center gap-2 bg-navy hover:bg-navy-800 text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg mb-6"
          onClick={() => alert('Démo : dans la version réelle, un ZIP contenant tous les documents vérifiés est téléchargé.')}>
          <Archive className="w-4 h-4" />Télécharger le dossier complet (ZIP)
        </button>

        <div className="bg-gradient-to-br from-primary-light/60 to-blue-50 border border-blue-200 rounded-2xl p-6 text-center">
          <h3 className="font-extrabold text-navy text-lg mb-2">Ça vous plaît ?</h3>
          <p className="text-sm text-navy-600 mb-4">Testez AutoDoc Pro sur vos vrais dossiers — 5 premiers dossiers sans avance de frais.</p>
          <a href="/#contact" className="inline-flex items-center gap-2 bg-emerald hover:bg-emerald-dark text-white px-6 py-3 rounded-xl font-bold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
            Commencer mon essai
          </a>
        </div>
      </div>
    </div>
  )
}

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [raison, setRaison] = useState('')
  const [siret, setSiret] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setLoading(true); setError('')
    try {
      if (mode === 'login') {
        const form = new URLSearchParams()
        form.append('username', email)
        form.append('password', password)
        const res = await fetch(`${API}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: form.toString(),
        })
        if (!res.ok) { setError('Email ou mot de passe incorrect'); setLoading(false); return }
        const data = await res.json()
        saveAuth(data.access_token, data.pro_id)
      } else {
        if (!raison.trim()) { setError('La raison sociale est requise'); setLoading(false); return }
        const res = await fetch(`${API}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, raison_sociale: raison, siret: siret || undefined }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          setError(err.detail || 'Erreur lors de la creation du compte')
          setLoading(false); return
        }
        const data = await res.json()
        saveAuth(data.access_token, data.pro_id)
      }
      onLogin()
    } catch { setError('Erreur de connexion au serveur') }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 max-w-md w-full">
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-emerald flex items-center justify-center mx-auto mb-3">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-extrabold text-navy tracking-tight">AutoDoc Pro</h1>
          <p className="text-sm text-slate-500 mt-1">{mode === 'login' ? 'Connectez-vous a votre espace' : 'Creez votre compte pro'}</p>
        </div>

        <div className="flex gap-2 mb-6">
          {(['login', 'register'] as const).map(m => (
            <button key={m} onClick={() => { setMode(m); setError('') }}
              className={`flex-1 py-2 rounded-xl text-sm font-medium border-2 transition-all ${
                mode === m ? 'border-primary bg-primary-light/30 text-primary' : 'border-slate-200 text-slate-500'
              }`}>
              {m === 'login' ? 'Connexion' : 'Inscription'}
            </button>
          ))}
        </div>

        <div className="space-y-3">
          {mode === 'register' && (
            <>
              <input value={raison} onChange={e => setRaison(e.target.value)} placeholder="Raison sociale"
                className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
              <input value={siret} onChange={e => setSiret(e.target.value)} placeholder="SIRET (optionnel — renseignable plus tard)"
                className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
            </>
          )}
          <input value={email} onChange={e => setEmail(e.target.value)} type="email" placeholder="Email"
            className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
          <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Mot de passe"
            onKeyDown={e => e.key === 'Enter' && submit()}
            className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" />
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-600 flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />{error}
          </div>
        )}

        <button onClick={submit} disabled={loading || !email || !password}
          className="w-full mt-4 inline-flex items-center justify-center gap-2 bg-emerald hover:bg-emerald-dark text-white py-3 rounded-2xl font-bold text-sm disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
          {mode === 'login' ? 'Se connecter' : 'Creer mon compte'}
        </button>
      </div>
    </div>
  )
}


function ProApp() {
  const [page, setPage] = useState<Page>('dashboard')
  const [selectedId, setSelectedId] = useState('')
  const [typeCompte, setTypeCompte] = useState('VENDEUR_HABILITE')
  const [authed, setAuthed] = useState(!!getToken())

  useEffect(() => {
    if (!authed) return
    fetch(`${API}/professionnel/profil?pro_id=${getProId()}`).then(r => {
      if (!r.ok) { clearAuth(); setAuthed(false); return null }
      return r.json()
    }).then((p: any) => { if (p?.type_compte) setTypeCompte(p.type_compte) }).catch(() => {})
  }, [authed])

  if (!authed) return <LoginPage onLogin={() => setAuthed(true)} />

  const handleDashboardSelect = (id: string, status: string) => {
    setSelectedId(id)
    if (status === 'CERFA_GENERE') setPage('dossier-complet')
    else setPage('workspace-dossier')
  }

  const typeLabels: Record<string, string> = {
    VENDEUR_HABILITE: 'Vendeur habilité',
    VENDEUR_NON_HABILITE: 'Vendeur',
    AGENT_HABILITE: 'Agent habilité',
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar current={page} onNav={setPage} badge={typeLabels[typeCompte]} onLogout={() => { clearAuth(); setAuthed(false) }} />
      <div className="max-w-6xl mx-auto px-6 py-8 pb-16">
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
