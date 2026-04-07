import { useState, useEffect } from 'react'
import {
  Lock, CheckCircle2, XCircle, Circle, AlertCircle, AlertTriangle,
  FileText, Download, Upload, Camera, Pencil, Trash2, Send,
  Shield, Mail, MapPin, Building2, Loader2, Info, ChevronRight,
  CircleDot, Zap, X,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface ClientPageData {
  dossier_id: string; reference: string; type: string | null; status?: string
  commerce: { nom: string | null; adresse: string | null; telephone: string | null }
  rgpd: any; consentement: { requis: boolean; accepte: boolean; texte: string }
  choix_cpi: { requis: boolean; choisi: boolean; mode: string | null; email: string | null; options: any[] }
  cession: { signature_requise: boolean; signee: boolean; telechargee: boolean }
  mentions_legales: any; intro_checklist: string; documents_attendus: any[]
  checklist: any; session: { message: string }; message?: string; prochaines_etapes?: any[]; contact?: string
}

// ─── Composant principal ────────────────────────────────────────────────────

export default function ClientPage({ token }: { token: string }) {
  const [data, setData] = useState<ClientPageData | null>(null)
  const [error, setError] = useState('')

  const reload = () => {
    fetch(`${API}/client/${token}`).then(r => r.json()).then(setData).catch(() => setError('Lien invalide'))
  }
  useEffect(() => { reload() }, [token])

  if (error) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 max-w-md text-center">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <Lock className="w-7 h-7 text-red-400" />
        </div>
        <h1 className="text-xl font-extrabold text-navy tracking-tight mb-2">Lien invalide</h1>
        <p className="text-slate-500 text-sm">Ce lien n'est plus actif ou a expiré.</p>
      </div>
    </div>
  )

  if (!data) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin text-primary" />
        <p className="text-sm text-slate-400">Chargement...</p>
      </div>
    </div>
  )

  if (data.status === 'termine') return <ClientTermine data={data} />

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-lg mx-auto py-6 px-4">
        {/* En-tête de confiance */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4 text-center">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-emerald flex items-center justify-center mx-auto mb-3">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div className="text-xl font-extrabold text-navy tracking-tight">{data.commerce.nom || 'Votre vendeur'}</div>
          {data.commerce.adresse && (
            <div className="text-sm text-slate-500 mt-1 flex items-center justify-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> {data.commerce.adresse}
            </div>
          )}
          <div className="text-xs text-slate-400 mt-3 flex items-center justify-center gap-1">
            a choisi <span className="inline-flex items-center gap-1 font-bold text-navy"><Zap className="w-3 h-3 text-primary" /> AutoDoc Pro</span> pour votre démarche de carte grise
          </div>
        </div>

        {/* Étape 1 : Consentement */}
        {!data.consentement.accepte && <StepConsent data={data} token={token} onDone={reload} />}

        {/* Étape 2 : Choix CPI */}
        {data.consentement.accepte && !data.choix_cpi.choisi && <StepChoixCPI data={data} token={token} onDone={reload} />}

        {/* Étape 3 : Signature cession */}
        {data.consentement.accepte && data.choix_cpi.choisi && data.cession.signature_requise && !data.cession.signee && (
          <StepSignCession token={token} onDone={reload} />
        )}
        {data.cession.signee && !data.cession.telechargee && <StepDownloadCession token={token} onDone={reload} />}

        {/* Étape 4 : Documents — checklist avec upload intégré par pièce */}
        {data.consentement.accepte && data.choix_cpi.choisi && (!data.cession.signature_requise || data.cession.telechargee) && (
          <>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 mb-4">
              <p className="text-sm text-slate-600 flex items-start gap-2">
                <Info className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                {data.intro_checklist}
              </p>
            </div>

            <DocumentChecklist data={data} token={token} onReload={reload} />

            {/* Alertes détectées sur les documents déjà déposés */}
            {data.checklist?.alertes?.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-4">
                <h3 className="flex items-center gap-2 font-bold text-navy mb-3">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  Corrections nécessaires
                </h3>
                <div className="space-y-2">
                  {data.checklist.alertes.map((alerte: any, i: number) => (
                    <div key={i} className={`text-xs p-3 rounded-xl flex items-start gap-2 ${
                      alerte.type === 'erreur'
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}>
                      {alerte.type === 'erreur'
                        ? <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        : <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                      }
                      {alerte.message}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data.checklist?.ready_for_diagnostic && <StepConfirmEnvoi data={data} token={token} />}
          </>
        )}

        <div className="text-center text-xs text-slate-400 mt-6 px-4">{data.session?.message}</div>
      </div>
    </div>
  )
}

// ─── Checklist avec upload intégré par pièce ────────────────────────────────

function DocumentChecklist({ data, token, onReload }: { data: ClientPageData; token: string; onReload: () => void }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-4">
      <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
        <FileText className="w-4 h-4 text-primary" />
        Documents à déposer
      </h3>
      {data.documents_attendus?.map((doc: any, i: number) => (
        <DocumentSlot key={i} doc={doc} data={data} token={token} onReload={onReload} />
      ))}
    </div>
  )
}

function DocumentSlot({ doc, data, token, onReload }: { doc: any; data: ClientPageData; token: string; onReload: () => void }) {
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<{ text: string; status: string } | null>(null)
  const [editing, setEditing] = useState(false)

  const isRectoVerso = doc.type === 'CNI' || doc.type === 'PERMIS'

  // Trouver les docs déjà déposés pour ce type
  const deposedDocs = (data.checklist?.documents || []).filter((d: any) =>
    d.type === doc.type || (doc.type === 'CNI' && d.type === 'PASSEPORT')
  )
  const nbOk = deposedDocs.filter((d: any) => d.status === 'ok').length
  const deposedFilenames = deposedDocs.map((d: any) => d.filename).filter(Boolean)

  // Restaurer l'info faces depuis la checklist serveur ou depuis le dernier upload
  const serverFaces = deposedDocs.find((d: any) => d.faces)?.faces || null
  const [facesInfo, setFacesInfo] = useState<any>(null)

  // Synchroniser avec les données serveur au rechargement
  useEffect(() => {
    if (serverFaces) setFacesInfo(serverFaces)
  }, [data])

  // Le document est complet si :
  // - Pour un doc recto/verso : le backend dit complet (faces.complet)
  // - Pour un doc simple : au moins 1 upload ok
  const isComplete = facesInfo
    ? facesInfo.complet
    : (nbOk >= 1 && !isRectoVerso)

  // Il manque encore des faces (recto/verso incomplet)
  const needsMore = isRectoVerso && facesInfo && !facesInfo.complet && nbOk >= 1

  // Afficher la zone d'upload si :
  // - rien n'a été déposé encore
  // - il manque des faces
  // - le client est en mode modification
  const showUpload = (nbOk === 0 && !facesInfo) || needsMore || editing

  const uploadFile = async (file: File, label: string, isCaptured: boolean = false) => {
    setUploading(true); setUploadMsg(null)
    const form = new FormData()
    form.append('file', file)
    form.append('source', 'client')
    form.append('doc_type', doc.type)
    if (isCaptured) form.append('captured_by_camera', 'true')
    try {
      const res = await fetch(`${API}/documents/${data.dossier_id}/upload`, { method: 'POST', body: form })
      const result = await res.json()

      // Mettre à jour l'info faces depuis le backend
      if (result.faces) setFacesInfo(result.faces)

      if (result.quality?.status === 'illisible') {
        setUploadMsg({ text: result.quality.message || 'Document illisible — re-déposez', status: 'error' })
      } else if (result.faces?.complet) {
        setUploadMsg({ text: 'Document complet — toutes les informations ont été lues.', status: 'ok' })
        setEditing(false)
      } else if (result.faces && !result.faces.complet && result.faces.recto_verso) {
        setUploadMsg({
          text: result.faces.message || 'Déposez l\'autre face du document.',
          status: 'warning',
        })
      } else if (result.quality?.status === 'avertissement') {
        setUploadMsg({ text: `${label} reçu — qualité moyenne`, status: 'warning' })
        setEditing(false)
      } else {
        setUploadMsg({ text: `${label} bien reçu`, status: 'ok' })
        setEditing(false)
      }
    } catch (e) {
      setUploadMsg({ text: 'Erreur lors du dépôt', status: 'error' })
    }
    setUploading(false)
    onReload()
  }

  const deleteDoc = async () => {
    await fetch(`${API}/client/${token}/document/${doc.type}`, { method: 'DELETE' })
    setUploadMsg(null)
    setFacesInfo(null)
    setEditing(false)
    onReload()
  }

  const startEdit = () => {
    setEditing(true)
    setUploadMsg(null)
  }

  // Affichage de l'état des faces
  const showFaceBadges = isRectoVerso && facesInfo && !facesInfo.complet

  return (
    <div className="py-3.5 border-b border-slate-100 last:border-0">
      {/* Titre + statut */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          {isComplete
            ? <CheckCircle2 className="w-5 h-5 text-emerald flex-shrink-0" />
            : nbOk >= 1
              ? <CircleDot className="w-5 h-5 text-amber-500 flex-shrink-0" />
              : doc.obligatoire
                ? <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                : <Circle className="w-5 h-5 text-slate-300 flex-shrink-0" />
          }
          <div>
            <div className="text-sm font-semibold text-navy">{doc.label}</div>
            {doc.raison && <div className="text-xs text-red-500 mt-0.5">{doc.raison}</div>}
            {doc.info && !doc.obligatoire && <div className="text-xs text-slate-400 mt-0.5">{doc.info}</div>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {showFaceBadges && (
            <div className="flex gap-1">
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium border ${
                facesInfo.recto_present ? 'bg-emerald-light text-emerald border-emerald/20' : 'bg-slate-100 text-slate-400 border-slate-200'
              }`}>
                {facesInfo.recto_present && <CheckCircle2 className="w-3 h-3" />} Recto
              </span>
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium border ${
                facesInfo.verso_present ? 'bg-emerald-light text-emerald border-emerald/20' : 'bg-slate-100 text-slate-400 border-slate-200'
              }`}>
                {facesInfo.verso_present && <CheckCircle2 className="w-3 h-3" />} Verso
              </span>
            </div>
          )}
          {nbOk >= 1 && !editing && (
            <button onClick={startEdit}
              className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary-dark font-semibold transition-colors">
              <Pencil className="w-3 h-3" /> Modifier
            </button>
          )}
        </div>
      </div>

      {/* Fichier(s) déposé(s) — visible quand le doc est ok */}
      {nbOk >= 1 && !editing && (
        <div className="ml-7 text-xs text-slate-500">
          {deposedFilenames.map((f: string, i: number) => (
            <span key={i} className="inline-flex items-center gap-1 bg-slate-50 border border-slate-100 rounded-lg px-2 py-0.5 mr-1">
              <FileText className="w-3 h-3 text-slate-400" /> {f}
            </span>
          ))}
        </div>
      )}

      {/* Zone upload */}
      {showUpload && (
        <div className="ml-7 mt-2">
          <div className="space-y-2">
            {editing && (
              <div className="flex items-center justify-between mb-1.5">
                <div className="text-xs text-slate-500">
                  Déposez le nouveau document pour remplacer l'ancien.
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setEditing(false); setUploadMsg(null) }}
                    className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors">
                    <X className="w-3 h-3" /> Annuler
                  </button>
                  <button onClick={deleteDoc}
                    className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-600 transition-colors">
                    <Trash2 className="w-3 h-3" /> Supprimer
                  </button>
                </div>
              </div>
            )}
            {!editing && isRectoVerso && !facesInfo && (
              <div className="text-xs text-slate-500 mb-1.5 flex items-start gap-1.5">
                <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-400" />
                Déposez une ou deux photos/fichiers. Le système détecte automatiquement chaque face.
              </div>
            )}
            {!editing && needsMore && (
              <div className="text-xs text-amber-600 mb-1.5 flex items-start gap-1.5 bg-amber-50 p-2 rounded-lg border border-amber-100">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                {facesInfo.message}
              </div>
            )}
            <UploadRow uploading={uploading}
              onFile={(f) => uploadFile(f, doc.label)}
              onCapture={(f) => uploadFile(f, doc.label, true)} />
          </div>
        </div>
      )}

      {/* Feedback upload */}
      {uploadMsg && (
        <div className={`ml-7 mt-2 text-xs p-2.5 rounded-xl flex items-start gap-1.5 ${
          uploadMsg.status === 'ok' ? 'bg-emerald-light/50 text-emerald-dark border border-emerald/20' :
          uploadMsg.status === 'error' ? 'bg-red-50 text-red-600 border border-red-200' :
          'bg-amber-50 text-amber-700 border border-amber-200'
        }`}>
          {uploadMsg.status === 'ok' ? <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" /> :
           uploadMsg.status === 'error' ? <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" /> :
           <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />}
          {uploadMsg.text}
        </div>
      )}
    </div>
  )
}

function UploadRow({ uploading, onFile, onCapture }: { uploading: boolean; onFile: (f: File) => void; onCapture?: (f: File) => void }) {
  const id = `upload-${Math.random()}`
  return (
    <div className="flex items-center gap-2">
      <input type="file" className="hidden" id={id} accept="image/*,application/pdf"
        onChange={e => e.target.files?.[0] && onFile(e.target.files[0])} />
      <label htmlFor={id}
        className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-dark text-white px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 hover:shadow-md hover:shadow-primary/20">
        {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
        {uploading ? 'Analyse...' : 'Fichier'}
      </label>
      <input type="file" className="hidden" id={`${id}-cam`} accept="image/*" capture="environment"
        onChange={e => e.target.files?.[0] && (onCapture || onFile)(e.target.files[0])} />
      <label htmlFor={`${id}-cam`}
        className="inline-flex items-center gap-1.5 bg-emerald hover:bg-emerald-dark text-white px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 hover:shadow-md hover:shadow-emerald/20">
        {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
        {uploading ? 'Analyse...' : 'Photo'}
      </label>
    </div>
  )
}

// ─── Étapes (Consentement, CPI, Cession, Confirmation) ─────────────────────

function StepConsent({ data, token, onDone }: { data: ClientPageData; token: string; onDone: () => void }) {
  const [checked, setChecked] = useState(false)
  const [loading, setLoading] = useState(false)
  const accept = async () => {
    setLoading(true)
    await fetch(`${API}/client/${token}/consent`, { method: 'POST' })
    setLoading(false); onDone()
  }
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
      <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
        <Shield className="w-5 h-5 text-primary" />
        Protection de vos données
      </h3>
      <div className="text-xs text-slate-500 space-y-1.5 mb-4">
        <div><strong className="text-navy-700">Responsable :</strong> {data.rgpd.responsable}</div>
        <div><strong className="text-navy-700">Finalité :</strong> {data.rgpd.finalite}</div>
        <div><strong className="text-navy-700">Base légale :</strong> {data.rgpd.base_legale}</div>
        <div><strong className="text-navy-700">Conservation :</strong> {data.rgpd.conservation}</div>
        <div><strong className="text-navy-700">Vos droits :</strong> {data.rgpd.droits}</div>
      </div>
      <div className="text-xs text-slate-400 p-3 bg-slate-50 rounded-xl border border-slate-100 mb-4">
        <div>{data.mentions_legales?.authenticite}</div>
        <div className="mt-1">{data.mentions_legales?.exactitude}</div>
      </div>
      <label className="flex gap-3 items-start cursor-pointer mb-4 p-3 rounded-xl border border-slate-200 hover:border-primary/30 transition-colors">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)}
          className="mt-1 rounded border-slate-300 text-primary focus:ring-primary/20" />
        <span className="text-sm text-navy-700">{data.consentement.texte}</span>
      </label>
      <button onClick={accept} disabled={!checked || loading}
        className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
        {loading ? 'Enregistrement...' : 'Continuer'}
      </button>
    </div>
  )
}

function StepChoixCPI({ data, token, onDone }: { data: ClientPageData; token: string; onDone: () => void }) {
  const [mode, setMode] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async () => {
    if (!mode) return
    setLoading(true)
    await fetch(`${API}/client/${token}/choix-cpi`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, email: mode === 'email' ? email : null }),
    })
    setLoading(false); onDone()
  }
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
      <h3 className="flex items-center gap-2 font-bold text-navy mb-2">
        <Mail className="w-5 h-5 text-primary" />
        Comment recevoir votre CPI ?
      </h3>
      <p className="text-xs text-slate-500 mb-4 ml-7">Le CPI vous permettra de circuler pendant 1 mois.</p>
      <div className="space-y-2 mb-4">
        {data.choix_cpi.options?.map((opt: any) => (
          <label key={opt.id}
            className={`flex items-start gap-3 p-3.5 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
              mode === opt.id
                ? 'border-primary bg-primary-light/30 shadow-sm'
                : 'border-slate-200 hover:border-slate-300'
            }`}>
            <input type="radio" name="cpi" value={opt.id} checked={mode === opt.id} onChange={() => setMode(opt.id)}
              className="mt-1 text-primary focus:ring-primary/20" />
            <span className={`text-sm ${mode === opt.id ? 'text-navy font-medium' : 'text-navy-700'}`}>{opt.label}</span>
          </label>
        ))}
      </div>
      {mode === 'email' && (
        <div className="mb-4">
          <input value={email} onChange={e => setEmail(e.target.value)} type="email"
            className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            placeholder="mon.email@exemple.fr" />
        </div>
      )}
      <button onClick={submit} disabled={!mode || loading || (mode === 'email' && !email.includes('@'))}
        className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
        {loading ? 'Enregistrement...' : 'Continuer'}
      </button>
    </div>
  )
}

function StepSignCession({ token, onDone }: { token: string; onDone: () => void }) {
  const [loading, setLoading] = useState(false)
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
      <h3 className="flex items-center gap-2 font-bold text-navy mb-2">
        <FileText className="w-5 h-5 text-primary" />
        Signature du certificat de cession
      </h3>
      <p className="text-sm text-slate-600 mb-4 ml-7">Vous allez signer le certificat de cession. C'est la dernière étape avant le dépôt de vos documents.</p>
      <button onClick={async () => { setLoading(true); await fetch(`${API}/client/${token}/signer-cession`, { method: 'POST' }); setLoading(false); onDone() }}
        disabled={loading}
        className="w-full inline-flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-primary/20">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
        {loading ? 'Signature...' : 'Signer le certificat de cession'}
      </button>
    </div>
  )
}

function StepDownloadCession({ token, onDone }: { token: string; onDone: () => void }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
      <h3 className="flex items-center gap-2 font-bold text-navy mb-2">
        <Download className="w-5 h-5 text-emerald" />
        Téléchargez votre certificat de cession
      </h3>
      <p className="text-sm text-slate-600 mb-4 ml-7">Ce document est obligatoire — conservez-le précieusement.</p>
      <button onClick={async () => { await fetch(`${API}/client/${token}/telecharger-cession`); onDone() }}
        className="w-full inline-flex items-center justify-center gap-2 bg-emerald hover:bg-emerald-dark text-white py-3 rounded-xl font-semibold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
        <Download className="w-4 h-4" />
        Télécharger mon certificat de cession
      </button>
    </div>
  )
}

function StepConfirmEnvoi({ data, token }: { data: ClientPageData; token: string }) {
  const [checked, setChecked] = useState(false)
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [result, setResult] = useState<any>(null)

  const confirm = async () => {
    setLoading(true)
    const res = await fetch(`${API}/client/${token}/confirmer-envoi`, { method: 'POST' })
    setResult(await res.json()); setSent(true); setLoading(false)
  }

  if (sent && result) return (
    <div className="bg-emerald-light/30 rounded-2xl shadow-sm border border-emerald/20 p-6 mb-4">
      <div className="text-center mb-4">
        <div className="w-14 h-14 rounded-full bg-emerald-light flex items-center justify-center mx-auto mb-3">
          <CheckCircle2 className="w-7 h-7 text-emerald" />
        </div>
        <h3 className="font-extrabold text-emerald-dark text-lg tracking-tight">{result.message}</h3>
      </div>
      <div className="space-y-2.5 text-sm text-emerald-dark/80">
        <div className="font-bold text-emerald-dark">Prochaines étapes :</div>
        {result.prochaines_etapes?.map((e: string, i: number) => (
          <div key={i} className="flex gap-2.5 items-start">
            <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">{i + 1}</span>
            <span>{e}</span>
          </div>
        ))}
      </div>
      {result.contact && <div className="text-xs text-emerald-dark/60 mt-4 text-center">{result.contact}</div>}
    </div>
  )

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
      <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
        <Send className="w-5 h-5 text-primary" />
        Vérifiez et confirmez
      </h3>
      <div className="mb-4 bg-slate-50 rounded-xl p-3 border border-slate-100">
        {data.checklist?.documents?.filter((d: any) => d.status === 'ok').map((d: any, i: number) => (
          <div key={i} className="flex items-center gap-2 text-sm py-1">
            <CheckCircle2 className="w-4 h-4 text-emerald" />
            <span className="text-navy-700">{d.type}</span>
          </div>
        ))}
      </div>
      <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-700 mb-4 flex items-start gap-2">
        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        Votre carte grise sera envoyée à l'adresse figurant sur votre justificatif de domicile. Vérifiez qu'elle est correcte.
      </div>
      <label className="flex gap-3 items-start cursor-pointer mb-4 p-3 rounded-xl border border-slate-200 hover:border-primary/30 transition-colors">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)}
          className="mt-1 rounded border-slate-300 text-primary focus:ring-primary/20" />
        <span className="text-sm text-navy-700">Je confirme l'envoi de mes documents à {data.commerce.nom || 'mon vendeur'} pour ma demande de carte grise.</span>
      </label>
      <button onClick={confirm} disabled={!checked || loading}
        className="w-full inline-flex items-center justify-center gap-2 bg-emerald hover:bg-emerald-dark text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        {loading ? 'Envoi...' : 'Envoyer mes documents'}
      </button>
    </div>
  )
}

function ClientTermine({ data }: { data: ClientPageData }) {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 max-w-md">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-emerald-light flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-emerald" />
          </div>
          <h1 className="text-xl font-extrabold text-navy tracking-tight">{data.message}</h1>
        </div>
        {data.prochaines_etapes && (
          <div className="space-y-3 text-sm text-slate-600">
            {data.prochaines_etapes.map((e: any, i: number) => (
              <div key={i} className="flex gap-3 items-start">
                <span className="w-6 h-6 rounded-full bg-primary-light flex items-center justify-center text-xs font-bold text-primary flex-shrink-0">{i + 1}</span>
                <span>{typeof e === 'string' ? e : e.description}</span>
              </div>
            ))}
          </div>
        )}
        {data.contact && <div className="text-xs text-slate-400 mt-6 text-center">{data.contact}</div>}
      </div>
    </div>
  )
}
