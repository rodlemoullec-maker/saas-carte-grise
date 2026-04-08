/**
 * Imatra — Application locale (version 2.0)
 *
 * Logiciel installé localement chez l'agent habilité SIV.
 * Communique uniquement avec le backend FastAPI sur localhost:8001.
 * Aucune dépendance cloud, aucune authentification multi-tenant.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import {
  AlertCircle, AlertTriangle, ArrowLeft, Check, CheckCircle2,
  Download, FileText, Inbox, Info, Key, Layers, Loader2, Mail,
  MailOpen, Package, Plus, RefreshCw, Search, Settings, Shield, Trash2, Users,
  Zap,
} from 'lucide-react'

// ─── Configuration ─────────────────────────────────────────────────────────

// En dev, Vite proxie /api → http://127.0.0.1:8001
// En prod (Docker), FastAPI sert directement sans préfixe.
const API = import.meta.env.DEV ? '/api' : ''

// ─── Types ─────────────────────────────────────────────────────────────────

interface Dossier {
  id: string
  reference: string
  type: string | null
  status: string
  diagnostic: string | null
  vin: string | null
  immatriculation: string | null
  client_nom: string | null
  client_prenom: string | null
  tax_estimate: any | null
  created_at: string
  updated_at: string
}

interface AgentProfile {
  id: string
  raison_sociale: string
  siret: string | null
  email: string
  nom_commerce: string | null
  adresse: string | null
  code_postal: string | null
  ville: string | null
  numero_habilitation: string | null
  cachet_path: string | null
  signature_path: string | null
  setup_complete: boolean
}

interface LicenseStatus {
  is_valid: boolean
  mode: string  // licensed | trial | expired | none
  payload: any | null
  trial_days_remaining: number | null
  trial_dossiers_used: number
  message: string
}

interface RulesStatus {
  version: string
  description: string
  source: string
  last_check: string | null
}

type Page = 'dashboard' | 'dossiers' | 'dossier-detail' | 'clients' | 'parametres'

// ─── API helpers ───────────────────────────────────────────────────────────

async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`)
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`)
  return r.json()
}

async function apiPost<T>(path: string, body?: any): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`POST ${path} → ${r.status}`)
  return r.json()
}

async function apiPut<T>(path: string, body?: any): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`PUT ${path} → ${r.status}`)
  return r.json()
}

async function apiDelete(path: string): Promise<void> {
  const r = await fetch(`${API}${path}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`DELETE ${path} → ${r.status}`)
}

async function apiUpload<T>(path: string, file: File, extra?: Record<string, string>): Promise<T> {
  const fd = new FormData()
  fd.append('file', file)
  if (extra) {
    for (const [k, v] of Object.entries(extra)) fd.append(k, v)
  }
  const r = await fetch(`${API}${path}`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error(`UPLOAD ${path} → ${r.status}`)
  return r.json()
}

// ─── Composants génériques ─────────────────────────────────────────────────

function Spinner({ className = '' }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} />
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    PENDING:        { color: 'bg-slate-100 text-slate-600 border-slate-200',     label: 'En attente' },
    DIAGNOSTIC:     { color: 'bg-blue-50 text-blue-700 border-blue-200',         label: 'Diagnostic' },
    CORRECTION:     { color: 'bg-amber-50 text-amber-700 border-amber-200',      label: 'À corriger' },
    CERFA_GENERE:   { color: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Cerfa prêt' },
    SOUMIS:         { color: 'bg-sky-50 text-sky-700 border-sky-200',            label: 'Soumis SIV' },
    CLOSED:         { color: 'bg-slate-50 text-slate-500 border-slate-200',      label: 'Clôturé' },
  }
  const cfg = map[status] || { color: 'bg-slate-50 text-slate-500 border-slate-200', label: status }
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function DiagnosticBadge({ diagnostic }: { diagnostic: string | null }) {
  if (!diagnostic) return null
  const map: Record<string, { color: string; label: string }> = {
    VERT:   { color: 'bg-emerald-500 text-white',   label: '🟢 VERT' },
    ORANGE: { color: 'bg-amber-500 text-white',     label: '🟠 ORANGE' },
    ROUGE:  { color: 'bg-red-500 text-white',       label: '🔴 ROUGE' },
  }
  const cfg = map[diagnostic] || { color: 'bg-slate-300 text-slate-700', label: diagnostic }
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

// ─── Navigation ────────────────────────────────────────────────────────────

function Sidebar({ current, onNav }: { current: Page; onNav: (p: Page) => void }) {
  const items: { id: Page; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard',  label: 'Tableau de bord', icon: <Inbox className="w-4 h-4" /> },
    { id: 'dossiers',   label: 'Dossiers',         icon: <Layers className="w-4 h-4" /> },
    { id: 'clients',    label: 'Clients',          icon: <Users className="w-4 h-4" /> },
    { id: 'parametres', label: 'Paramètres',       icon: <Settings className="w-4 h-4" /> },
  ]
  return (
    <aside className="w-56 min-h-screen bg-white border-r border-slate-200 flex flex-col">
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
          </span>
          <div>
            <div className="text-sm font-extrabold text-slate-900">Imatra</div>
            <div className="text-[10px] text-slate-400">Local — v2.0</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-2">
        {items.map(item => {
          const active = current === item.id || (item.id === 'dossiers' && current === 'dossier-detail')
          return (
            <button
              key={item.id}
              onClick={() => onNav(item.id)}
              className={`w-full flex items-center gap-2 px-3 py-2 mb-1 text-sm font-medium rounded-lg transition-all ${
                active
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          )
        })}
      </nav>
      <div className="p-3 border-t border-slate-100 text-[10px] text-slate-400">
        Logiciel installé localement.<br />
        Vos données ne quittent pas cette machine.
      </div>
    </aside>
  )
}

// ─── Bannière licence ──────────────────────────────────────────────────────

function LicenseBanner({ status }: { status: LicenseStatus | null }) {
  if (!status) return null
  if (status.mode === 'licensed') return null  // Pas de bannière si licence active
  const colors: Record<string, string> = {
    trial:   'bg-amber-50 border-amber-200 text-amber-800',
    expired: 'bg-red-50 border-red-200 text-red-800',
    none:    'bg-slate-50 border-slate-200 text-slate-700',
  }
  const cls = colors[status.mode] || colors.none
  return (
    <div className={`px-4 py-2 border-b text-sm ${cls}`}>
      <div className="max-w-6xl mx-auto flex items-center gap-2">
        {status.mode === 'expired'
          ? <AlertCircle className="w-4 h-4" />
          : <Info className="w-4 h-4" />}
        <span>{status.message}</span>
      </div>
    </div>
  )
}

// ─── Zone drag & drop emails ───────────────────────────────────────────────

interface DropResult {
  email?: any
  attachments_processed?: any[]
  attachments_skipped?: any[]
  suggested_dossier?: any
  next_action?: string
  message?: string
  dossier_id?: string
  draft_dossier_id?: string
}

function EmailDropZone({ onProcessed }: { onProcessed: (result: DropResult) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setBusy(true)
    setError(null)
    try {
      const file = files[0]
      const result = await apiUpload<DropResult>('/emails/upload', file)
      onProcessed(result)
    } catch (e: any) {
      setError(e?.message || 'Erreur lors du traitement de l\'email')
    } finally {
      setBusy(false)
    }
  }, [onProcessed])

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
      className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
        dragOver
          ? 'border-blue-500 bg-blue-50'
          : 'border-slate-300 bg-white hover:border-slate-400'
      } ${busy ? 'opacity-60 pointer-events-none' : ''}`}
    >
      {busy ? (
        <div className="flex flex-col items-center gap-3 text-blue-600">
          <Spinner className="w-8 h-8" />
          <div className="text-sm font-medium">Lecture de l'email et OCR en cours…</div>
        </div>
      ) : (
        <>
          <MailOpen className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-slate-800 mb-1">
            Glissez ici un email ou des documents
          </h3>
          <p className="text-sm text-slate-500 mb-4">
            Formats acceptés : .eml, .msg, ou pièces jointes (PDF, JPG, PNG) directement
          </p>
          <button
            onClick={() => inputRef.current?.click()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            Ou cliquer pour sélectionner
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".eml,.msg,.pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </>
      )}
      {error && (
        <div className="mt-4 text-sm text-red-600 flex items-center gap-2 justify-center">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
    </div>
  )
}

// ─── Popup proposition de rattachement ─────────────────────────────────────

function MatchPopup({
  result,
  onConfirm,
  onCreateNew,
  onClose,
}: {
  result: DropResult
  onConfirm: () => void
  onCreateNew: () => void
  onClose: () => void
}) {
  const suggested = result.suggested_dossier
  if (!suggested) return null

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0">
            <Info className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Document déjà connu ?
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Ce document semble appartenir à un dossier existant.
            </p>
          </div>
        </div>

        <div className="bg-slate-50 rounded-xl p-4 mb-4 text-sm">
          <div className="font-mono text-xs text-slate-500 mb-2">{suggested.reference}</div>
          <div className="font-semibold text-slate-900">
            {suggested.client_prenom} {suggested.client_nom || '(client inconnu)'}
          </div>
          {suggested.vin && (
            <div className="text-xs text-slate-500 mt-1">VIN : {suggested.vin}</div>
          )}
          {suggested.immatriculation && (
            <div className="text-xs text-slate-500">Immatriculation : {suggested.immatriculation}</div>
          )}
          <div className="mt-2 text-[11px] text-slate-400">
            Confiance : {Math.round((suggested.confidence || 0) * 100)}% — raison : {suggested.match_reason}
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg"
          >
            Ajouter à ce dossier
          </button>
          <button
            onClick={onCreateNew}
            className="flex-1 px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-lg"
          >
            Créer un nouveau dossier
          </button>
        </div>
        <button
          onClick={onClose}
          className="mt-2 w-full text-xs text-slate-400 hover:text-slate-600"
        >
          Annuler
        </button>
      </div>
    </div>
  )
}

// ─── Carte dossier ─────────────────────────────────────────────────────────

function DossierCard({ dossier, onClick }: { dossier: Dossier; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white border border-slate-200 hover:border-blue-300 hover:shadow-md rounded-xl p-4 transition-all"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-slate-500">{dossier.reference}</span>
        <div className="flex gap-1">
          <DiagnosticBadge diagnostic={dossier.diagnostic} />
          <StatusBadge status={dossier.status} />
        </div>
      </div>
      <div className="font-semibold text-slate-900">
        {dossier.client_prenom} {dossier.client_nom || '(client inconnu)'}
      </div>
      <div className="text-xs text-slate-500 mt-1">
        {dossier.type ? `${dossier.type} · ` : ''}
        {dossier.immatriculation || dossier.vin || 'Véhicule à identifier'}
      </div>
    </button>
  )
}

// ─── Page Dashboard ────────────────────────────────────────────────────────

function DashboardPage({
  onOpenDossier,
  refreshKey,
}: {
  onOpenDossier: (id: string) => void
  refreshKey: number
}) {
  const [recent, setRecent] = useState<Dossier[]>([])
  const [loading, setLoading] = useState(true)
  const [matchPopup, setMatchPopup] = useState<DropResult | null>(null)

  const loadRecent = useCallback(async () => {
    try {
      setLoading(true)
      const dossiers = await apiGet<Dossier[]>('/dossiers/?limit=8')
      setRecent(dossiers)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadRecent() }, [loadRecent, refreshKey])

  const handleProcessed = (result: DropResult) => {
    if (result.next_action === 'confirm_attach_or_create') {
      setMatchPopup(result)
    } else if (result.dossier_id) {
      onOpenDossier(result.dossier_id)
    }
    void loadRecent()
  }

  const handleAttachToExisting = async () => {
    if (!matchPopup?.suggested_dossier?.id) return
    // Pas de réupload — le draft a déjà les pièces. On ouvre le dossier suggéré
    // (la migration définitive du draft → dossier existant viendra plus tard)
    onOpenDossier(matchPopup.suggested_dossier.id)
    setMatchPopup(null)
  }

  const handleCreateNew = () => {
    if (matchPopup?.draft_dossier_id) {
      onOpenDossier(matchPopup.draft_dossier_id)
    }
    setMatchPopup(null)
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Tableau de bord</h1>
      <p className="text-sm text-slate-500 mb-6">
        Glissez un email reçu de votre client pour démarrer un dossier.
      </p>

      <EmailDropZone onProcessed={handleProcessed} />

      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-slate-900">Dossiers récents</h2>
          <button
            onClick={() => void loadRecent()}
            className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Actualiser
          </button>
        </div>
        {loading ? (
          <div className="flex justify-center py-8 text-slate-400">
            <Spinner className="w-6 h-6" />
          </div>
        ) : recent.length === 0 ? (
          <div className="text-center py-8 text-sm text-slate-400">
            Aucun dossier pour l'instant. Glissez un email pour commencer.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recent.map(d => (
              <DossierCard key={d.id} dossier={d} onClick={() => onOpenDossier(d.id)} />
            ))}
          </div>
        )}
      </div>

      {matchPopup && (
        <MatchPopup
          result={matchPopup}
          onConfirm={handleAttachToExisting}
          onCreateNew={handleCreateNew}
          onClose={() => setMatchPopup(null)}
        />
      )}
    </div>
  )
}

// ─── Page Liste des dossiers ───────────────────────────────────────────────

function DossiersListPage({ onOpen }: { onOpen: (id: string) => void }) {
  const [dossiers, setDossiers] = useState<Dossier[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('')

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiGet<Dossier[]>('/dossiers/?limit=100')
        setDossiers(data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = dossiers.filter(d => !filter || d.status === filter)

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Tous les dossiers</h1>
      <p className="text-sm text-slate-500 mb-6">{dossiers.length} dossier(s) sur cette installation.</p>

      <div className="flex gap-2 mb-4">
        {['', 'PENDING', 'DIAGNOSTIC', 'CERFA_GENERE'].map(s => (
          <button
            key={s || 'all'}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg ${
              filter === s
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {s ? s.replace('_', ' ') : 'Tous'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12 text-slate-400">
          <Spinner className="w-6 h-6" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filtered.map(d => (
            <DossierCard key={d.id} dossier={d} onClick={() => onOpen(d.id)} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Page Détail dossier ───────────────────────────────────────────────────

function CerfaPreview({ dossierId, refreshKey }: { dossierId: string; refreshKey: number }) {
  // Aperçu live du Cerfa : refresh à chaque changement de refreshKey
  // (ajout d'un document, lancement diagnostic, etc.) + cache-buster sur l'URL.
  const [tick, setTick] = useState(0)
  useEffect(() => { setTick(t => t + 1) }, [refreshKey])
  const src = `${API}/dossiers/${dossierId}/cerfa-preview?t=${tick}`
  return (
    <div className="mb-4 border border-slate-200 rounded-lg overflow-hidden bg-slate-50">
      <div className="px-3 py-2 text-xs text-slate-500 bg-white border-b border-slate-200 flex items-center justify-between">
        <span>Aperçu Cerfa (mise à jour automatique)</span>
        <button
          onClick={() => setTick(t => t + 1)}
          className="text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" /> Rafraîchir
        </button>
      </div>
      <img
        src={src}
        alt="Aperçu Cerfa"
        className="w-full max-h-[600px] object-contain bg-white"
        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
      />
    </div>
  )
}

function DossierDetailPage({ dossierId, onBack }: { dossierId: string; onBack: () => void }) {
  const [admin, setAdmin] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [relanceText, setRelanceText] = useState<any | null>(null)
  const [archiveReminder, setArchiveReminder] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiGet<any>(`/dossiers/${dossierId}/admin`)
      setAdmin(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [dossierId])

  useEffect(() => { void load() }, [load])

  const runDiagnostic = async () => {
    setRunning(true)
    try {
      await apiPost(`/dossiers/${dossierId}/run-diagnostic`)
      await load()
    } catch (e: any) {
      alert(`Diagnostic impossible : ${e?.message}`)
    } finally {
      setRunning(false)
    }
  }

  const generateCerfa = async () => {
    setRunning(true)
    try {
      await apiGet(`/dossiers/${dossierId}/cerfa`)
      await load()
      setArchiveReminder(true)
    } catch (e: any) {
      alert(`Cerfa impossible : ${e?.message}`)
    } finally {
      setRunning(false)
    }
  }

  const generateRelance = async () => {
    try {
      const data = await apiGet<any>(`/dossiers/${dossierId}/relance-email`)
      setRelanceText(data)
    } catch (e: any) {
      alert(`Erreur : ${e?.message}`)
    }
  }

  const downloadZip = () => {
    window.open(`${API}/dossiers/${dossierId}/download-zip`, '_blank')
  }

  const deleteDossier = async () => {
    if (!confirm('Supprimer ce dossier et tous ses documents ?')) return
    try {
      await apiDelete(`/dossiers/${dossierId}`)
      onBack()
    } catch (e: any) {
      alert(`Erreur : ${e?.message}`)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12 text-slate-400">
        <Spinner className="w-6 h-6" />
      </div>
    )
  }
  if (!admin) {
    return <div className="p-6 text-slate-500">Dossier introuvable.</div>
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-3">
        <ArrowLeft className="w-4 h-4" /> Retour
      </button>

      <div className="bg-white border border-slate-200 rounded-2xl p-6 mb-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="font-mono text-xs text-slate-500">{admin.reference}</div>
            <h1 className="text-2xl font-bold text-slate-900">
              {admin.client_prenom} {admin.client_nom || '(client inconnu)'}
            </h1>
            <div className="text-sm text-slate-500 mt-1">
              {admin.type ? `${admin.type} · ` : ''}
              {admin.immatriculation || admin.vin || 'Véhicule à identifier'}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <DiagnosticBadge diagnostic={admin.diagnostic} />
            <StatusBadge status={admin.status} />
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={runDiagnostic}
            disabled={running}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white text-sm font-semibold rounded-lg flex items-center gap-2"
          >
            {running ? <Spinner className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
            Lancer le diagnostic
          </button>
          <button
            onClick={generateCerfa}
            disabled={running}
            className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white text-sm font-semibold rounded-lg flex items-center gap-2"
          >
            <FileText className="w-4 h-4" />
            Générer le Cerfa
          </button>
          <button
            onClick={generateRelance}
            className="px-3 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-lg flex items-center gap-2"
          >
            <Mail className="w-4 h-4" />
            Email de relance
          </button>
          <button
            onClick={downloadZip}
            className="px-3 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-lg flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Télécharger ZIP
          </button>
          <button
            onClick={deleteDossier}
            className="px-3 py-2 bg-white border border-red-200 hover:bg-red-50 text-red-600 text-sm font-semibold rounded-lg flex items-center gap-2 ml-auto"
          >
            <Trash2 className="w-4 h-4" />
            Supprimer
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
            <Package className="w-4 h-4" /> Documents
          </h3>
          <CerfaPreview dossierId={dossierId} refreshKey={admin?.documents_vendeur?.length || 0} />
          {(admin.documents_vendeur || []).length === 0 ? (
            <p className="text-xs text-slate-400">Aucun document pour l'instant.</p>
          ) : (
            <ul className="space-y-2">
              {(admin.documents_vendeur || []).map((doc: any) => (
                <li key={doc.id} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700">
                    <span className="font-mono text-xs text-slate-400 mr-2">{doc.type}</span>
                    {doc.filename}
                  </span>
                  {doc.status === 'EXTRACTED' && <Check className="w-4 h-4 text-emerald-500" />}
                  {doc.status === 'REJECTED' && <AlertCircle className="w-4 h-4 text-red-500" />}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Blocages
          </h3>
          {(admin.blocages || []).length === 0 ? (
            <p className="text-xs text-slate-400">Aucun blocage détecté.</p>
          ) : (
            <ul className="space-y-2 text-sm text-slate-700">
              {(admin.blocages || []).map((b: any, i: number) => (
                <li key={i} className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-mono text-[10px] text-slate-400">{b.code}</div>
                    <div>{b.message}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {admin.tax_estimate && (
        <div className="mt-4 bg-white border border-slate-200 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4" /> Estimation taxes
          </h3>
          <pre className="text-xs text-slate-600 overflow-auto">
            {JSON.stringify(admin.tax_estimate, null, 2)}
          </pre>
        </div>
      )}

      {archiveReminder && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">Cerfa généré — pensez à archiver</h3>
                <p className="text-sm text-slate-600 mt-1">
                  Conservez le dossier <strong>5 ans</strong> sur un support sécurisé conformément à
                  l'article R322-9 du Code de la route. Téléchargez le ZIP enrichi
                  (manifeste + SHA256) et stockez-le dans votre archive.
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { setArchiveReminder(false); downloadZip() }}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg inline-flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" /> Télécharger ZIP
              </button>
              <button
                onClick={() => setArchiveReminder(false)}
                className="px-4 py-2 text-slate-600 hover:text-slate-900 text-sm"
              >Plus tard</button>
            </div>
          </div>
        </div>
      )}

      {relanceText && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-6 max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold">Email de relance pré-rédigé</h3>
              <button onClick={() => setRelanceText(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <div className="text-xs text-slate-500 mb-2">Sujet :</div>
            <div className="bg-slate-50 rounded-lg p-3 mb-3 text-sm font-mono">{relanceText.subject}</div>
            <div className="text-xs text-slate-500 mb-2">Corps :</div>
            <pre className="bg-slate-50 rounded-lg p-3 text-sm font-mono whitespace-pre-wrap text-slate-800">{relanceText.body}</pre>
            <button
              onClick={() => {
                navigator.clipboard.writeText(`Sujet : ${relanceText.subject}\n\n${relanceText.body}`)
                alert('Copié dans le presse-papier !')
              }}
              className="mt-3 w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg"
            >
              Copier dans le presse-papier
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Page Clients ──────────────────────────────────────────────────────────

type Client = {
  id: string
  type: string
  display_name: string
  nom: string | null
  prenom: string | null
  date_naissance: string | null
  lieu_naissance: string | null
  raison_sociale: string | null
  siret: string | null
  representant_legal: string | null
  email: string | null
  telephone: string | null
  adresse: string | null
  code_postal: string | null
  ville: string | null
  pays: string | null
  notes: string | null
  nb_dossiers: number
  dernier_dossier_at: string | null
}

const EMPTY_CLIENT: Partial<Client> = {
  type: 'PHYSIQUE',
  nom: '', prenom: '', date_naissance: '', lieu_naissance: '',
  raison_sociale: '', siret: '', representant_legal: '',
  email: '', telephone: '',
  adresse: '', code_postal: '', ville: '', pays: 'France',
  notes: '',
}

function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<Partial<Client> | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiGet<{ clients: Client[] }>(`/clients${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      setClients(data.clients)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q])

  useEffect(() => { void load() }, [load])

  const save = async () => {
    if (!editing) return
    setSaving(true)
    setError(null)
    try {
      const payload: any = { ...editing }
      delete payload.id; delete payload.display_name
      delete payload.nb_dossiers; delete payload.dernier_dossier_at
      if (editing.id) {
        await apiPut(`/clients/${editing.id}`, payload)
      } else {
        await apiPost('/clients', payload)
      }
      setEditing(null)
      await load()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: string) => {
    if (!confirm('Supprimer ce client ?')) return
    try {
      await apiDelete(`/clients/${id}`)
      await load()
    } catch (e: any) {
      setError(e.message)
    }
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Clients</h1>
        <button
          onClick={() => setEditing({ ...EMPTY_CLIENT })}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg"
        >
          <Plus className="w-4 h-4" /> Nouveau client
        </button>
      </div>

      <div className="mb-4 relative">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Rechercher par nom, raison sociale, SIRET, email, téléphone…"
          className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin mx-auto" />
          </div>
        ) : clients.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">Aucun client enregistré.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2">Nom / Raison sociale</th>
                <th className="text-left px-4 py-2">Type</th>
                <th className="text-left px-4 py-2">Contact</th>
                <th className="text-left px-4 py-2">Dossiers</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {clients.map(c => (
                <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-900">{c.display_name}</td>
                  <td className="px-4 py-2 text-slate-500">{c.type === 'MORALE' ? 'Personne morale' : 'Particulier'}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {c.email && <div>{c.email}</div>}
                    {c.telephone && <div>{c.telephone}</div>}
                  </td>
                  <td className="px-4 py-2 text-slate-500">{c.nb_dossiers}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => setEditing(c)}
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium mr-3"
                    >Éditer</button>
                    <button
                      onClick={() => remove(c.id)}
                      className="text-red-600 hover:text-red-800 text-xs font-medium"
                    >Supprimer</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-auto">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">
                {editing.id ? 'Modifier le client' : 'Nouveau client'}
              </h2>
              <button onClick={() => setEditing(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-600">Type</label>
                <select
                  value={editing.type}
                  onChange={e => setEditing({ ...editing, type: e.target.value })}
                  className="w-full mt-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="PHYSIQUE">Particulier</option>
                  <option value="MORALE">Personne morale</option>
                </select>
              </div>

              {editing.type === 'MORALE' ? (
                <div className="grid grid-cols-2 gap-3">
                  <ClientField label="Raison sociale" value={editing.raison_sociale} onChange={v => setEditing({ ...editing, raison_sociale: v })} />
                  <ClientField label="SIRET" value={editing.siret} onChange={v => setEditing({ ...editing, siret: v })} />
                  <ClientField label="Représentant légal" value={editing.representant_legal} onChange={v => setEditing({ ...editing, representant_legal: v })} className="col-span-2" />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <ClientField label="Nom" value={editing.nom} onChange={v => setEditing({ ...editing, nom: v })} />
                  <ClientField label="Prénom" value={editing.prenom} onChange={v => setEditing({ ...editing, prenom: v })} />
                  <ClientField label="Date de naissance" value={editing.date_naissance} onChange={v => setEditing({ ...editing, date_naissance: v })} placeholder="JJ/MM/AAAA" />
                  <ClientField label="Lieu de naissance" value={editing.lieu_naissance} onChange={v => setEditing({ ...editing, lieu_naissance: v })} />
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <ClientField label="Email" value={editing.email} onChange={v => setEditing({ ...editing, email: v })} />
                <ClientField label="Téléphone" value={editing.telephone} onChange={v => setEditing({ ...editing, telephone: v })} />
              </div>

              <ClientField label="Adresse" value={editing.adresse} onChange={v => setEditing({ ...editing, adresse: v })} />
              <div className="grid grid-cols-3 gap-3">
                <ClientField label="Code postal" value={editing.code_postal} onChange={v => setEditing({ ...editing, code_postal: v })} />
                <ClientField label="Ville" value={editing.ville} onChange={v => setEditing({ ...editing, ville: v })} className="col-span-2" />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-600">Notes</label>
                <textarea
                  value={editing.notes || ''}
                  onChange={e => setEditing({ ...editing, notes: e.target.value })}
                  rows={3}
                  className="w-full mt-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>
            </div>
            <div className="p-6 border-t border-slate-200 flex justify-end gap-2">
              <button
                onClick={() => setEditing(null)}
                className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900"
              >Annuler</button>
              <button
                onClick={save}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white text-sm font-medium rounded-lg"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ClientField({ label, value, onChange, placeholder, className }: {
  label: string; value: string | null | undefined; onChange: (v: string) => void;
  placeholder?: string; className?: string;
}) {
  return (
    <div className={className}>
      <label className="text-xs font-medium text-slate-600">{label}</label>
      <input
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full mt-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
      />
    </div>
  )
}

// ─── Page Paramètres ───────────────────────────────────────────────────────

function ParametresPage() {
  const [agent, setAgent] = useState<AgentProfile | null>(null)
  const [license, setLicense] = useState<LicenseStatus | null>(null)
  const [rules, setRules] = useState<RulesStatus | null>(null)
  const [licenseToken, setLicenseToken] = useState('')
  const [loading, setLoading] = useState(true)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [a, l, r] = await Promise.all([
        apiGet<AgentProfile>('/agent'),
        apiGet<LicenseStatus>('/license/status'),
        apiGet<RulesStatus>('/rules/status'),
      ])
      setAgent(a)
      setLicense(l)
      setRules(r)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadAll() }, [loadAll])

  const saveAgent = async () => {
    if (!agent) return
    try {
      await apiPost('/agent', agent)
      alert('Profil enregistré.')
      void loadAll()
    } catch (e: any) {
      alert(`Erreur : ${e?.message}`)
    }
  }

  const activateLicense = async () => {
    if (!licenseToken.trim()) return
    try {
      await apiPost('/license/activate', { token: licenseToken.trim() })
      setLicenseToken('')
      void loadAll()
    } catch (e: any) {
      alert(`Activation impossible : ${e?.message}`)
    }
  }

  const checkRulesUpdate = async () => {
    try {
      const result = await apiPost<any>('/rules/check-update?force=true')
      alert(result.message || 'Vérification effectuée.')
      void loadAll()
    } catch (e: any) {
      alert(`Erreur : ${e?.message}`)
    }
  }

  if (loading || !agent) {
    return (
      <div className="flex justify-center py-12 text-slate-400">
        <Spinner className="w-6 h-6" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Paramètres</h1>

      {/* Profil agent */}
      <section className="bg-white border border-slate-200 rounded-2xl p-6">
        <h2 className="text-base font-semibold mb-4 flex items-center gap-2">
          <Settings className="w-4 h-4" /> Profil de l'agent
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Raison sociale" value={agent.raison_sociale}
            onChange={v => setAgent({ ...agent, raison_sociale: v })} />
          <Field label="SIRET" value={agent.siret || ''}
            onChange={v => setAgent({ ...agent, siret: v })} />
          <Field label="Email" value={agent.email}
            onChange={v => setAgent({ ...agent, email: v })} />
          <Field label="Nom commerce" value={agent.nom_commerce || ''}
            onChange={v => setAgent({ ...agent, nom_commerce: v })} />
          <Field label="Adresse" value={agent.adresse || ''}
            onChange={v => setAgent({ ...agent, adresse: v })} />
          <Field label="Code postal" value={agent.code_postal || ''}
            onChange={v => setAgent({ ...agent, code_postal: v })} />
          <Field label="Ville" value={agent.ville || ''}
            onChange={v => setAgent({ ...agent, ville: v })} />
          <Field label="N° habilitation SIV" value={agent.numero_habilitation || ''}
            onChange={v => setAgent({ ...agent, numero_habilitation: v })} />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={saveAgent}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg"
          >
            Enregistrer
          </button>
          {agent.setup_complete && (
            <span className="text-xs text-emerald-600 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Profil complet
            </span>
          )}
        </div>

        {/* Cachet et signature — requis pour traiter un email */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <AssetUpload
            label="Cachet (avec signature dessus)"
            currentPath={agent.cachet_path}
            endpoint="/agent/cachet"
            onUploaded={loadAll}
          />
        </div>
      </section>

      {/* Licence */}
      <section className="bg-white border border-slate-200 rounded-2xl p-6">
        <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
          <Key className="w-4 h-4" /> Licence
        </h2>
        {license && (
          <div className="mb-4 text-sm">
            <div className="font-medium text-slate-700">{license.message}</div>
            {license.payload && (
              <div className="text-xs text-slate-500 mt-1">
                {license.payload.agent_email} · type {license.payload.type}
              </div>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Collez votre token de licence ici..."
            value={licenseToken}
            onChange={e => setLicenseToken(e.target.value)}
            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono"
          />
          <button
            onClick={activateLicense}
            disabled={!licenseToken.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white text-sm font-semibold rounded-lg"
          >
            Activer
          </button>
        </div>
      </section>

      {/* Règles paramétrables */}
      <section className="bg-white border border-slate-200 rounded-2xl p-6">
        <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4" /> Règles paramétrables
        </h2>
        {rules && (
          <div className="mb-4 text-sm">
            <div className="text-slate-700">
              Version <span className="font-mono font-semibold">{rules.version}</span>
              <span className="text-xs text-slate-400 ml-2">({rules.source})</span>
            </div>
            {rules.description && (
              <div className="text-xs text-slate-500 mt-1">{rules.description}</div>
            )}
            {rules.last_check && (
              <div className="text-xs text-slate-400 mt-1">
                Dernière vérification : {new Date(rules.last_check).toLocaleString('fr-FR')}
              </div>
            )}
          </div>
        )}
        <button
          onClick={checkRulesUpdate}
          className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-lg flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Vérifier les mises à jour
        </button>
      </section>
    </div>
  )
}

function AssetUpload({ label, currentPath, endpoint, onUploaded }: {
  label: string; currentPath: string | null; endpoint: string; onUploaded: () => void;
}) {
  const [busy, setBusy] = useState(false)
  const handleFile = async (f: File | undefined) => {
    if (!f) return
    setBusy(true)
    try {
      await apiUpload(endpoint, f)
      onUploaded()
    } catch (e: any) {
      alert(`Upload échoué : ${e?.message}`)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="border border-dashed border-slate-300 rounded-lg p-4">
      <div className="text-xs text-slate-500 mb-2">{label}</div>
      <div className="flex items-center gap-2">
        <label className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded cursor-pointer">
          {busy ? 'Envoi…' : currentPath ? 'Remplacer' : 'Choisir un fichier'}
          <input type="file" accept="image/*" className="hidden"
            onChange={e => handleFile(e.target.files?.[0])} />
        </label>
        {currentPath && (
          <span className="text-xs text-emerald-600 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> chargé
          </span>
        )}
      </div>
    </div>
  )
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="block text-xs text-slate-500 mb-1">{label}</span>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-blue-400 focus:outline-none"
      />
    </label>
  )
}

// ─── App principale ────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [currentDossierId, setCurrentDossierId] = useState<string | null>(null)
  const [license, setLicense] = useState<LicenseStatus | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // Charger l'état de licence au démarrage et le rafraîchir périodiquement
  useEffect(() => {
    const loadLicense = async () => {
      try {
        const status = await apiGet<LicenseStatus>('/license/status')
        setLicense(status)
      } catch (e) {
        console.error('License status error', e)
      }
    }
    void loadLicense()
    const interval = setInterval(loadLicense, 60_000)  // toutes les minutes
    return () => clearInterval(interval)
  }, [])

  const openDossier = (id: string) => {
    setCurrentDossierId(id)
    setPage('dossier-detail')
  }

  const goBack = () => {
    setPage('dossiers')
    setCurrentDossierId(null)
    setRefreshKey(k => k + 1)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      <Sidebar current={page} onNav={setPage} />
      <div className="flex-1 flex flex-col">
        <LicenseBanner status={license} />
        <main className="flex-1">
          {page === 'dashboard' && (
            <DashboardPage onOpenDossier={openDossier} refreshKey={refreshKey} />
          )}
          {page === 'dossiers' && (
            <DossiersListPage onOpen={openDossier} />
          )}
          {page === 'dossier-detail' && currentDossierId && (
            <DossierDetailPage dossierId={currentDossierId} onBack={goBack} />
          )}
          {page === 'clients' && <ClientsPage />}
          {page === 'parametres' && <ParametresPage />}
        </main>
      </div>
    </div>
  )
}
