import { useState, useEffect } from 'react'
import {
  Building2, MapPin, Shield, Mail, ChevronRight, Loader2,
  Lock, CheckCircle2, Circle, AlertCircle, Upload, Camera,
  FileText, Info, Zap, Car, CircleDot, Pencil, X,
  AlertTriangle, XCircle,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface PublicPageData {
  slug: string
  type_compte: string
  commerce: { nom: string | null; adresse: string | null; ville: string | null; telephone: string | null }
  intro: string
  rgpd: any
  consentement_texte: string
  choix_cpi_options: any[]
  intention_type_options: any[]
}

// ─── Composant principal ────────────────────────────────────────────────────

export default function PublicClientPage({ slug }: { slug: string }) {
  const [pageData, setPageData] = useState<PublicPageData | null>(null)
  const [error, setError] = useState('')

  // Étapes du flux
  const [step, setStep] = useState<'form' | 'upload' | 'done'>('form')
  const [dossierId, setDossierId] = useState<string | null>(null)
  const [infoSuite, setInfoSuite] = useState('')
  const [docsAttendus, setDocsAttendus] = useState<any[]>([])

  useEffect(() => {
    fetch(`${API}/public/${slug}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setPageData)
      .catch(() => setError('Page non trouvée'))
  }, [slug])

  if (error) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 max-w-md text-center">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <Lock className="w-7 h-7 text-red-400" />
        </div>
        <h1 className="text-xl font-extrabold text-navy tracking-tight mb-2">Page non trouvée</h1>
        <p className="text-slate-500 text-sm">Ce lien n'est pas valide ou ce commerce n'est pas encore inscrit.</p>
      </div>
    </div>
  )

  if (!pageData) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin text-primary" />
        <p className="text-sm text-slate-400">Chargement...</p>
      </div>
    </div>
  )

  const nomCommerce = pageData.commerce.nom || 'Votre vendeur'
  const isAgent = pageData.type_compte === 'AGENT_HABILITE'

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-lg mx-auto py-6 px-4">
        {/* En-tête de confiance */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4 text-center">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-emerald flex items-center justify-center mx-auto mb-3">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div className="text-xl font-extrabold text-navy tracking-tight">{nomCommerce}</div>
          {pageData.commerce.adresse && (
            <div className="text-sm text-slate-500 mt-1 flex items-center justify-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> {pageData.commerce.adresse}
              {pageData.commerce.ville && `, ${pageData.commerce.ville}`}
            </div>
          )}
          <div className="text-xs text-slate-400 mt-3 flex items-center justify-center gap-1">
            {isAgent ? 'Demande de carte grise' : 'Démarche carte grise'} via <span className="inline-flex items-center gap-1 font-bold text-navy"><Zap className="w-3 h-3 text-primary" /> AutoDoc Pro</span>
          </div>
        </div>

        {step === 'form' && (
          <PublicForm
            pageData={pageData}
            slug={slug}
            onCreated={(id, info, docs) => {
              setDossierId(id)
              setInfoSuite(info)
              setDocsAttendus(docs)
              setStep('upload')
            }}
          />
        )}

        {step === 'upload' && dossierId && (
          <PublicUpload
            dossierId={dossierId}
            docsAttendus={docsAttendus}
            infoSuite={infoSuite}
            nomCommerce={nomCommerce}
            onDone={() => setStep('done')}
          />
        )}

        {step === 'done' && (
          <PublicDone nomCommerce={nomCommerce} infoSuite={infoSuite} isAgent={isAgent} />
        )}

        <div className="text-center text-xs text-slate-400 mt-6">
          Vos documents sont traités de manière sécurisée et supprimés après finalisation du dossier.
        </div>
      </div>
    </div>
  )
}

// ─── Formulaire d'inscription ───────────────────────────────────────────────

function PublicForm({ pageData, slug, onCreated }: {
  pageData: PublicPageData
  slug: string
  onCreated: (dossierId: string, infoSuite: string, docs: any[]) => void
}) {
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [telephone, setTelephone] = useState('')
  const [email, setEmail] = useState('')
  const [intentionType, setIntentionType] = useState<string | null>(null)
  const [consent, setConsent] = useState(false)
  const [cpiMode, setCpiMode] = useState('')
  const [cpiEmail, setCpiEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const nomCommerce = pageData.commerce.nom || 'votre vendeur'

  const isAgent = pageData.type_compte === 'AGENT_HABILITE'
  const canSubmit = nom.trim() && prenom.trim() && telephone.trim() && consent && cpiMode
    && (cpiMode !== 'email' || cpiEmail.includes('@'))
    && (!isAgent || intentionType)  // Agent : type véhicule obligatoire

  const submit = async () => {
    if (!canSubmit) return
    setLoading(true); setError('')

    // 1. Créer le dossier
    const res = await fetch(`${API}/public/${slug}/dossier`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_nom: nom.trim().toUpperCase(),
        client_prenom: prenom.trim(),
        client_telephone: telephone.trim(),
        client_email: email.trim() || null,
        intention_type: intentionType,
      }),
    })
    if (!res.ok) {
      setError('Erreur lors de la création du dossier')
      setLoading(false)
      return
    }
    const data = await res.json()
    const dossierId = data.dossier_id

    // 2. Consentement RGPD
    await fetch(`${API}/public/${slug}/dossier/${dossierId}/consent`, { method: 'POST' })

    // 3. Choix CPI
    await fetch(`${API}/public/${slug}/dossier/${dossierId}/choix-cpi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: cpiMode, email: cpiMode === 'email' ? cpiEmail : null }),
    })

    setLoading(false)
    onCreated(dossierId, data.info_suite, data.docs_attendus)
  }

  return (
    <>
      {/* Info — adapté selon vendeur ou agent */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
          <div className="text-sm text-navy-700">
            {pageData.type_compte === 'AGENT_HABILITE' ? (
              <>
                <p>Déposez vos documents pour votre demande de carte grise auprès de <strong>{nomCommerce}</strong>. Ça prend 2 à 3 minutes.</p>
                <p className="mt-2 text-slate-500 text-xs">{nomCommerce} vérifiera votre dossier et soumettra la demande au SIV.</p>
              </>
            ) : (
              <>
                <p>Préparez votre dossier carte grise en déposant vos documents d'identité <strong>avant l'achat</strong>. Ça prend 2 à 3 minutes.</p>
                <p className="mt-2 text-slate-500 text-xs">Après l'achat de votre véhicule, si des documents complémentaires sont nécessaires, vous recevrez un SMS. Sinon, {nomCommerce} s'occupe du reste.</p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Formulaire */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
        <h3 className="flex items-center gap-2 font-bold text-navy mb-5">
          <FileText className="w-5 h-5 text-primary" />
          Vos informations
        </h3>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Nom *</label>
            <input value={nom} onChange={e => setNom(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="DUPONT" />
          </div>
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Prénom *</label>
            <input value={prenom} onChange={e => setPrenom(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="Marie" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Téléphone portable *</label>
            <input value={telephone} onChange={e => setTelephone(e.target.value)} type="tel"
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="06 12 34 56 78" />
          </div>
          <div>
            <label className="block text-xs font-medium text-navy-600 mb-1.5">Email</label>
            <input value={email} onChange={e => setEmail(e.target.value)} type="email"
              className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="marie@exemple.fr" />
          </div>
        </div>

        {/* Type de véhicule — obligatoire pour agent, optionnel pour vendeur */}
        <div className="mb-4">
          <label className="block text-xs font-medium text-navy-600 mb-2">
            <Car className="w-3.5 h-3.5 inline mr-1 text-slate-400" />
            {pageData.type_compte === 'AGENT_HABILITE'
              ? 'Type de véhicule *'
              : 'Type de véhicule envisagé'}
          </label>
          <div className="flex gap-2">
            {[
              { id: 'VN', label: 'Neuf' },
              { id: 'VO', label: 'Occasion' },
              { id: null, label: 'Je ne sais pas' },
            ].map(opt => (
              <button key={opt.id || 'null'} onClick={() => setIntentionType(opt.id)}
                className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium border-2 transition-all duration-200 ${
                  intentionType === opt.id
                    ? 'border-primary bg-primary-light/30 text-primary'
                    : 'border-slate-200 text-slate-500 hover:border-slate-300'
                }`}>
                {opt.label}
              </button>
            ))}
          </div>
          {intentionType === 'VO' && (
            <div className="mt-2 text-xs text-amber-600 bg-amber-50 p-2.5 rounded-xl border border-amber-100 flex items-start gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              Pour un véhicule d'occasion, vous serez contacté par SMS après l'achat pour signer le certificat de cession.
            </div>
          )}
          {intentionType === 'VN' && (
            <div className="mt-2 text-xs text-emerald-dark bg-emerald-light/50 p-2.5 rounded-xl border border-emerald/20 flex items-start gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              Sauf besoin de documents complémentaires selon le véhicule, vos documents devraient suffire.
            </div>
          )}
        </div>
      </div>

      {/* Choix CPI */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
        <h3 className="flex items-center gap-2 font-bold text-navy mb-2">
          <Mail className="w-5 h-5 text-primary" />
          Comment recevoir votre CPI ?
        </h3>
        <p className="text-xs text-slate-500 mb-4 ml-7">Le CPI vous permettra de circuler pendant 1 mois en attendant la carte grise.</p>
        <div className="space-y-2">
          {pageData.choix_cpi_options.map((opt: any) => (
            <label key={opt.id}
              className={`flex items-start gap-3 p-3.5 rounded-xl border-2 cursor-pointer transition-all duration-200 ${
                cpiMode === opt.id
                  ? 'border-primary bg-primary-light/30 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300'
              }`}>
              <input type="radio" name="cpi" value={opt.id} checked={cpiMode === opt.id}
                onChange={() => setCpiMode(opt.id)} className="mt-1 text-primary focus:ring-primary/20" />
              <span className={`text-sm ${cpiMode === opt.id ? 'text-navy font-medium' : 'text-navy-700'}`}>{opt.label}</span>
            </label>
          ))}
        </div>
        {cpiMode === 'email' && (
          <div className="mt-3">
            <input value={cpiEmail} onChange={e => setCpiEmail(e.target.value)} type="email"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              placeholder="mon.email@exemple.fr" />
          </div>
        )}
      </div>

      {/* Consentement RGPD */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-4">
        <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
          <Shield className="w-5 h-5 text-primary" />
          Protection de vos données
        </h3>
        <div className="text-xs text-slate-500 space-y-1.5 mb-4">
          <div><strong className="text-navy-700">Responsable :</strong> {pageData.rgpd.responsable}</div>
          <div><strong className="text-navy-700">Finalité :</strong> {pageData.rgpd.finalite}</div>
          <div><strong className="text-navy-700">Base légale :</strong> {pageData.rgpd.base_legale}</div>
          <div><strong className="text-navy-700">Conservation :</strong> {pageData.rgpd.conservation}</div>
          <div><strong className="text-navy-700">Vos droits :</strong> {pageData.rgpd.droits}</div>
        </div>
        <label className="flex gap-3 items-start cursor-pointer p-3 rounded-xl border border-slate-200 hover:border-primary/30 transition-colors">
          <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}
            className="mt-1 rounded border-slate-300 text-primary focus:ring-primary/20" />
          <span className="text-sm text-navy-700">{pageData.consentement_texte}</span>
        </label>
      </div>

      {/* Submit */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
        </div>
      )}
      <button onClick={submit} disabled={!canSubmit || loading}
        className="w-full inline-flex items-center justify-center gap-2 bg-emerald hover:bg-emerald-dark text-white py-3.5 rounded-2xl font-bold text-sm disabled:opacity-50 transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
        {loading ? 'Création du dossier...' : 'Continuer — déposer mes documents'}
      </button>
    </>
  )
}

// ─── Zone d'upload documents ────────────────────────────────────────────────

function PublicUpload({ dossierId, docsAttendus, infoSuite, nomCommerce: _nomCommerce, onDone }: {
  dossierId: string; docsAttendus: any[]; infoSuite: string; nomCommerce: string; onDone: () => void
}) {
  const [docs, setDocs] = useState(docsAttendus)
  const [allDone, setAllDone] = useState(false)

  const checkAllDone = (updatedDocs: any[]) => {
    const allComplete = updatedDocs.every(d => d._complete)
    setAllDone(allComplete)
  }

  const markComplete = (index: number) => {
    const updated = [...docs]
    updated[index] = { ...updated[index], _complete: true }
    setDocs(updated)
    checkAllDone(updated)
  }

  const addHebergementDocs = () => {
    const hasAttestation = docs.some(d => d.type === 'ATTESTATION_HEBERGEMENT')
    if (!hasAttestation) {
      const updated = [
        ...docs,
        { type: 'ATTESTATION_HEBERGEMENT', label: "Attestation d'hébergement", obligatoire: true, recto_verso: false, _added: true },
        { type: 'CNI_HEBERGEANT', label: "Pièce d'identité de l'hébergeant", obligatoire: true, recto_verso: true, _added: true },
      ]
      setDocs(updated)
    }
  }

  return (
    <>
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-4">
        <h3 className="flex items-center gap-2 font-bold text-navy mb-4">
          <Upload className="w-5 h-5 text-primary" />
          Documents à déposer
        </h3>
        {docs.map((doc: any, i: number) => (
          <PublicDocSlot key={`${doc.type}-${i}`} doc={doc} dossierId={dossierId}
            onComplete={() => markComplete(i)}
            onHebergementDetected={addHebergementDocs} />
        ))}
      </div>

      {infoSuite && (
        <div className="bg-primary-light/50 border border-blue-200 rounded-2xl p-4 mb-4 text-sm text-primary flex items-start gap-2">
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
          {infoSuite}
        </div>
      )}

      {allDone && (
        <button onClick={onDone}
          className="w-full inline-flex items-center justify-center gap-2 bg-emerald hover:bg-emerald-dark text-white py-3.5 rounded-2xl font-bold text-sm transition-all duration-200 hover:shadow-lg hover:shadow-emerald/20">
          <CheckCircle2 className="w-4 h-4" />
          Confirmer l'envoi de mes documents
        </button>
      )}
    </>
  )
}

// ─── Slot document individuel ───────────────────────────────────────────────

function PublicDocSlot({ doc, dossierId, onComplete, onHebergementDetected }: {
  doc: any; dossierId: string; onComplete: () => void; onHebergementDetected: () => void
}) {
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<{ text: string; status: string } | null>(null)
  const [complete, setComplete] = useState(false)
  const [editing, setEditing] = useState(false)
  const [filename, setFilename] = useState('')
  const [facesInfo, setFacesInfo] = useState<any>(null)

  const isRectoVerso = doc.recto_verso || doc.type === 'CNI' || doc.type === 'PERMIS'
  const needsMore = isRectoVerso && facesInfo && !facesInfo.complet

  const showUpload = !complete || needsMore || editing

  const uploadFile = async (file: File, isCaptured = false) => {
    setUploading(true); setUploadMsg(null)
    const form = new FormData()
    form.append('file', file)
    form.append('source', 'client')
    form.append('doc_type', doc.type)
    if (isCaptured) form.append('captured_by_camera', 'true')
    try {
      const res = await fetch(`${API}/documents/${dossierId}/upload`, { method: 'POST', body: form })
      const result = await res.json()

      if (result.faces) setFacesInfo(result.faces)

      // Détection hébergement
      if (result.hebergement_detecte) {
        onHebergementDetected()
      }

      if (result.quality?.status === 'illisible') {
        setUploadMsg({ text: result.quality.message || 'Document illisible — re-déposez', status: 'error' })
      } else if (result.faces?.complet) {
        setUploadMsg({ text: 'Document complet — toutes les informations ont été lues.', status: 'ok' })
        setComplete(true); setEditing(false); setFilename(file.name); onComplete()
      } else if (result.faces && !result.faces.complet && result.faces.recto_verso) {
        setUploadMsg({ text: result.faces.message || "Déposez l'autre face du document.", status: 'warning' })
        setFilename(file.name)
      } else if (result.quality?.status === 'avertissement') {
        setUploadMsg({ text: `${doc.label} reçu — qualité moyenne`, status: 'warning' })
        setComplete(true); setEditing(false); setFilename(file.name); onComplete()
      } else {
        setUploadMsg({ text: `${doc.label} bien reçu`, status: 'ok' })
        setComplete(true); setEditing(false); setFilename(file.name); onComplete()
      }
    } catch {
      setUploadMsg({ text: 'Erreur lors du dépôt', status: 'error' })
    }
    setUploading(false)
  }

  const uploadId = `pub-upload-${doc.type}-${Math.random()}`

  return (
    <div className="py-3.5 border-b border-slate-100 last:border-0">
      {/* Titre + statut */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          {complete
            ? <CheckCircle2 className="w-5 h-5 text-emerald flex-shrink-0" />
            : needsMore
              ? <CircleDot className="w-5 h-5 text-amber-500 flex-shrink-0" />
              : doc.obligatoire
                ? <Circle className="w-5 h-5 text-slate-300 flex-shrink-0" />
                : <Circle className="w-5 h-5 text-slate-300 flex-shrink-0" />
          }
          <span className="text-sm font-semibold text-navy">{doc.label}</span>
          {doc._added && (
            <span className="text-xs bg-amber-50 text-amber-600 px-2 py-0.5 rounded-full border border-amber-200 font-medium">Ajouté</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isRectoVerso && facesInfo && !facesInfo.complet && (
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
          {complete && !editing && (
            <button onClick={() => { setEditing(true); setUploadMsg(null) }}
              className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary-dark font-semibold transition-colors">
              <Pencil className="w-3 h-3" /> Modifier
            </button>
          )}
        </div>
      </div>

      {/* Fichier déposé */}
      {complete && !editing && filename && (
        <div className="ml-7 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1 bg-slate-50 border border-slate-100 rounded-lg px-2 py-0.5">
            <FileText className="w-3 h-3 text-slate-400" /> {filename}
          </span>
        </div>
      )}

      {/* Zone upload */}
      {showUpload && (
        <div className="ml-7 mt-2">
          {editing && (
            <div className="flex items-center justify-between mb-1.5">
              <div className="text-xs text-slate-500">Déposez le nouveau document pour remplacer.</div>
              <button onClick={() => { setEditing(false); setUploadMsg(null) }}
                className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors">
                <X className="w-3 h-3" /> Annuler
              </button>
            </div>
          )}
          {!editing && isRectoVerso && !facesInfo && (
            <div className="text-xs text-slate-500 mb-1.5 flex items-start gap-1.5">
              <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-400" />
              Déposez une ou deux photos. Le système détecte automatiquement chaque face.
            </div>
          )}
          {!editing && needsMore && facesInfo?.message && (
            <div className="text-xs text-amber-600 mb-1.5 flex items-start gap-1.5 bg-amber-50 p-2 rounded-lg border border-amber-100">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              {facesInfo.message}
            </div>
          )}
          <div className="flex items-center gap-2">
            <input type="file" className="hidden" id={uploadId} accept="image/*,application/pdf"
              onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0])} />
            <label htmlFor={uploadId}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-dark text-white px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 hover:shadow-md">
              {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
              {uploading ? 'Analyse...' : 'Fichier'}
            </label>
            <input type="file" className="hidden" id={`${uploadId}-cam`} accept="image/*" capture="environment"
              onChange={e => e.target.files?.[0] && uploadFile(e.target.files[0], true)} />
            <label htmlFor={`${uploadId}-cam`}
              className="inline-flex items-center gap-1.5 bg-emerald hover:bg-emerald-dark text-white px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 hover:shadow-md">
              {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
              {uploading ? 'Analyse...' : 'Photo'}
            </label>
          </div>
        </div>
      )}

      {/* Feedback */}
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

// ─── Écran de fin ───────────────────────────────────────────────────────────

function PublicDone({ nomCommerce, infoSuite, isAgent }: { nomCommerce: string; infoSuite: string; isAgent: boolean }) {
  return (
    <div className="bg-emerald-light/30 rounded-2xl shadow-sm border border-emerald/20 p-6">
      <div className="text-center mb-4">
        <div className="w-16 h-16 rounded-full bg-emerald-light flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 className="w-8 h-8 text-emerald" />
        </div>
        <h2 className="text-lg font-extrabold text-navy tracking-tight">Vos documents sont bien reçus !</h2>
      </div>

      <div className="space-y-3 text-sm text-emerald-dark/80">
        {infoSuite && (
          <div className="bg-white/60 rounded-xl p-3 border border-emerald/10 text-sm">
            {infoSuite}
          </div>
        )}
        <div className="bg-white/60 rounded-xl p-3 border border-emerald/10">
          <strong className="text-navy">Prochaines étapes :</strong>
          {isAgent ? (
            <div className="mt-2 space-y-2">
              <div className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">1</span>
                <span>{nomCommerce} vérifie votre dossier et prépare le Cerfa.</span>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">2</span>
                <span>La demande est soumise au SIV — vous recevez votre CPI.</span>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">3</span>
                <span>Votre carte grise définitive sera envoyée par courrier sécurisé à votre adresse.</span>
              </div>
            </div>
          ) : (
            <div className="mt-2 space-y-2">
              <div className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">1</span>
                <span>Après l'achat de votre véhicule, {nomCommerce} finalisera le dossier.</span>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">2</span>
                <span>Si des documents complémentaires sont nécessaires, vous recevrez un SMS.</span>
              </div>
              <div className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-emerald/10 flex items-center justify-center text-xs font-bold text-emerald flex-shrink-0">3</span>
                <span>Votre carte grise définitive sera envoyée par courrier sécurisé à votre adresse.</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
