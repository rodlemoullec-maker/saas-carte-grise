import { useState, useEffect } from 'react'

const API = 'http://localhost:8001'

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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
        <div className="text-4xl mb-4">&#128274;</div>
        <h1 className="text-xl font-bold text-gray-800 mb-2">Lien invalide</h1>
        <p className="text-gray-500">Ce lien n'est plus actif ou a expire.</p>
      </div>
    </div>
  )
  if (!data) return <div className="min-h-screen bg-gray-50 flex items-center justify-center"><div className="text-gray-400">Chargement...</div></div>
  if (data.status === 'termine') return <ClientTermine data={data} />

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-lg mx-auto py-6 px-4">
        {/* En-tete de confiance */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-4 text-center">
          <div className="text-2xl font-bold text-gray-800">{data.commerce.nom || 'Votre vendeur'}</div>
          {data.commerce.adresse && <div className="text-sm text-gray-500 mt-1">{data.commerce.adresse}</div>}
          <div className="text-xs text-gray-400 mt-2">a choisi <strong>AutoDoc Pro</strong> pour votre demarche de carte grise</div>
        </div>

        {/* Etape 1 : Consentement */}
        {!data.consentement.accepte && <StepConsent data={data} token={token} onDone={reload} />}

        {/* Etape 2 : Choix CPI */}
        {data.consentement.accepte && !data.choix_cpi.choisi && <StepChoixCPI data={data} token={token} onDone={reload} />}

        {/* Etape 3 : Signature cession */}
        {data.consentement.accepte && data.choix_cpi.choisi && data.cession.signature_requise && !data.cession.signee && (
          <StepSignCession token={token} onDone={reload} />
        )}
        {data.cession.signee && !data.cession.telechargee && <StepDownloadCession token={token} onDone={reload} />}

        {/* Etape 4 : Documents — checklist avec upload integre par piece */}
        {data.consentement.accepte && data.choix_cpi.choisi && (!data.cession.signature_requise || data.cession.telechargee) && (
          <>
            <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
              <p className="text-sm text-gray-600">{data.intro_checklist}</p>
            </div>

            <DocumentChecklist data={data} token={token} onReload={reload} />

            {data.checklist?.ready_for_diagnostic && <StepConfirmEnvoi data={data} token={token} />}
          </>
        )}

        <div className="text-center text-xs text-gray-400 mt-6 px-4">{data.session?.message}</div>
      </div>
    </div>
  )
}

// ─── Checklist avec upload integre par piece ────────────────────────────────

function DocumentChecklist({ data, token, onReload }: { data: ClientPageData; token: string; onReload: () => void }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
      <h3 className="font-bold text-gray-800 mb-3">Documents a deposer</h3>
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

  // Trouver les docs deja deposes pour ce type
  const deposedDocs = (data.checklist?.documents || []).filter((d: any) =>
    d.type === doc.type || (doc.type === 'CNI' && d.type === 'PASSEPORT')
  )
  const nbOk = deposedDocs.filter((d: any) => d.status === 'ok').length
  const deposedFilenames = deposedDocs.map((d: any) => d.filename).filter(Boolean)

  // Restaurer l'info faces depuis la checklist serveur ou depuis le dernier upload
  const serverFaces = deposedDocs.find((d: any) => d.faces)?.faces || null
  const [facesInfo, setFacesInfo] = useState<any>(null)

  // Synchroniser avec les donnees serveur au rechargement
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
  // - rien n'a ete depose encore
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

      // Mettre a jour l'info faces depuis le backend
      if (result.faces) setFacesInfo(result.faces)

      if (result.quality?.status === 'illisible') {
        setUploadMsg({ text: result.quality.message || 'Document illisible — re-deposez', status: 'error' })
      } else if (result.faces?.complet) {
        setUploadMsg({ text: 'Document complet — toutes les informations ont ete lues.', status: 'ok' })
        setEditing(false)
      } else if (result.faces && !result.faces.complet && result.faces.recto_verso) {
        setUploadMsg({
          text: result.faces.message || 'Deposez l\'autre face du document.',
          status: 'warning',
        })
      } else if (result.quality?.status === 'avertissement') {
        setUploadMsg({ text: `${label} recu — qualite moyenne`, status: 'warning' })
        setEditing(false)
      } else {
        setUploadMsg({ text: `${label} recu ✓`, status: 'ok' })
        setEditing(false)
      }
    } catch (e) {
      setUploadMsg({ text: 'Erreur lors du depot', status: 'error' })
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

  // Affichage de l'etat des faces
  const showFaceBadges = isRectoVerso && facesInfo && !facesInfo.complet

  return (
    <div className={`py-3 border-b last:border-0`}>
      {/* Titre + statut */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={isComplete ? 'text-green-500 text-lg' : nbOk >= 1 ? 'text-orange-400 text-lg' : doc.obligatoire ? 'text-red-400' : 'text-gray-300'}>
            {isComplete ? '✓' : nbOk >= 1 ? '◐' : '○'}
          </span>
          <div>
            <div className="text-sm font-medium">{doc.label}</div>
            {doc.raison && <div className="text-xs text-red-500">{doc.raison}</div>}
            {doc.info && !doc.obligatoire && <div className="text-xs text-gray-400">{doc.info}</div>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {showFaceBadges && (
            <div className="flex gap-1">
              <span className={`text-xs px-2 py-0.5 rounded ${facesInfo.recto_present ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
                {facesInfo.recto_present ? 'Recto ✓' : 'Recto'}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${facesInfo.verso_present ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
                {facesInfo.verso_present ? 'Verso ✓' : 'Verso'}
              </span>
            </div>
          )}
          {nbOk >= 1 && !editing && (
            <button onClick={startEdit} className="text-xs text-blue-500 hover:text-blue-700 font-medium">Modifier</button>
          )}
        </div>
      </div>

      {/* Fichier(s) depose(s) — visible quand le doc est ok */}
      {nbOk >= 1 && !editing && (
        <div className="ml-7 text-xs text-gray-500">
          {deposedFilenames.map((f: string, i: number) => (
            <span key={i} className="inline-flex items-center gap-1 bg-gray-50 rounded px-2 py-0.5 mr-1">
              {f}
            </span>
          ))}
        </div>
      )}

      {/* Zone upload */}
      {showUpload && (
        <div className="ml-7 mt-2">
          <div className="space-y-2">
            {editing && (
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-gray-500">
                  Deposez le nouveau document pour remplacer l'ancien.
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setEditing(false); setUploadMsg(null) }}
                    className="text-xs text-gray-400 hover:text-gray-600">Annuler</button>
                  <button onClick={deleteDoc}
                    className="text-xs text-red-400 hover:text-red-600">Supprimer</button>
                </div>
              </div>
            )}
            {!editing && isRectoVerso && !facesInfo && (
              <div className="text-xs text-gray-500 mb-1">
                Deposez une ou deux photos/fichiers. Le systeme detecte automatiquement chaque face.
              </div>
            )}
            {!editing && needsMore && (
              <div className="text-xs text-orange-600 mb-1">
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
        <div className={`ml-7 mt-2 text-xs p-2 rounded ${
          uploadMsg.status === 'ok' ? 'bg-green-50 text-green-600' :
          uploadMsg.status === 'error' ? 'bg-red-50 text-red-600' : 'bg-orange-50 text-orange-600'
        }`}>
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
      <label htmlFor={id} className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-xs cursor-pointer">
        {uploading ? 'Analyse...' : '📁 Fichier'}
      </label>
      <input type="file" className="hidden" id={`${id}-cam`} accept="image/*" capture="environment"
        onChange={e => e.target.files?.[0] && (onCapture || onFile)(e.target.files[0])} />
      <label htmlFor={`${id}-cam`} className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded text-xs cursor-pointer">
        {uploading ? 'Analyse...' : '📷 Photo'}
      </label>
    </div>
  )
}

// ─── Etapes (Consentement, CPI, Cession, Confirmation) ─────────────────────

function StepConsent({ data, token, onDone }: { data: ClientPageData; token: string; onDone: () => void }) {
  const [checked, setChecked] = useState(false)
  const [loading, setLoading] = useState(false)
  const accept = async () => {
    setLoading(true)
    await fetch(`${API}/client/${token}/consent`, { method: 'POST' })
    setLoading(false); onDone()
  }
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-4">
      <h3 className="font-bold text-gray-800 mb-3">Protection de vos donnees</h3>
      <div className="text-xs text-gray-500 space-y-1 mb-4">
        <div><strong>Responsable :</strong> {data.rgpd.responsable}</div>
        <div><strong>Finalite :</strong> {data.rgpd.finalite}</div>
        <div><strong>Base legale :</strong> {data.rgpd.base_legale}</div>
        <div><strong>Conservation :</strong> {data.rgpd.conservation}</div>
        <div><strong>Vos droits :</strong> {data.rgpd.droits}</div>
      </div>
      <div className="text-xs text-gray-400 p-3 bg-gray-50 rounded mb-4">
        <div>{data.mentions_legales?.authenticite}</div>
        <div className="mt-1">{data.mentions_legales?.exactitude}</div>
      </div>
      <label className="flex gap-3 items-start cursor-pointer mb-4">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} className="mt-1 rounded" />
        <span className="text-sm text-gray-700">{data.consentement.texte}</span>
      </label>
      <button onClick={accept} disabled={!checked || loading}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50">
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
    <div className="bg-white rounded-xl shadow-sm p-6 mb-4">
      <h3 className="font-bold text-gray-800 mb-3">Comment recevoir votre CPI ?</h3>
      <p className="text-xs text-gray-500 mb-4">Le CPI vous permettra de circuler pendant 1 mois.</p>
      <div className="space-y-3 mb-4">
        {data.choix_cpi.options?.map((opt: any) => (
          <label key={opt.id} className={`flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition ${mode === opt.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
            <input type="radio" name="cpi" value={opt.id} checked={mode === opt.id} onChange={() => setMode(opt.id)} className="mt-1" />
            <span className="text-sm">{opt.label}</span>
          </label>
        ))}
      </div>
      {mode === 'email' && (
        <div className="mb-4">
          <input value={email} onChange={e => setEmail(e.target.value)} type="email"
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm" placeholder="mon.email@exemple.fr" />
        </div>
      )}
      <button onClick={submit} disabled={!mode || loading || (mode === 'email' && !email.includes('@'))}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50">
        {loading ? 'Enregistrement...' : 'Continuer'}
      </button>
    </div>
  )
}

function StepSignCession({ token, onDone }: { token: string; onDone: () => void }) {
  const [loading, setLoading] = useState(false)
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-4">
      <h3 className="font-bold text-gray-800 mb-3">Signature du certificat de cession</h3>
      <p className="text-sm text-gray-600 mb-4">Vous allez signer le certificat de cession. C'est la derniere etape avant le depot de vos documents.</p>
      <button onClick={async () => { setLoading(true); await fetch(`${API}/client/${token}/signer-cession`, { method: 'POST' }); setLoading(false); onDone() }}
        disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50">
        {loading ? 'Signature...' : 'Signer le certificat de cession'}
      </button>
    </div>
  )
}

function StepDownloadCession({ token, onDone }: { token: string; onDone: () => void }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-4">
      <h3 className="font-bold text-gray-800 mb-3">Telechargez votre certificat de cession</h3>
      <p className="text-sm text-gray-600 mb-4">Ce document est obligatoire — conservez-le precieusement.</p>
      <button onClick={async () => { await fetch(`${API}/client/${token}/telecharger-cession`); onDone() }}
        className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-medium">
        Telecharger mon certificat de cession
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
    <div className="bg-green-50 rounded-xl shadow-sm p-6 mb-4">
      <div className="text-center mb-4">
        <div className="text-4xl mb-2">&#10003;</div>
        <h3 className="font-bold text-green-800 text-lg">{result.message}</h3>
      </div>
      <div className="space-y-2 text-sm text-green-700">
        <div className="font-medium">Prochaines etapes :</div>
        {result.prochaines_etapes?.map((e: string, i: number) => (
          <div key={i} className="flex gap-2"><span>{i + 1}.</span><span>{e}</span></div>
        ))}
      </div>
      {result.contact && <div className="text-xs text-green-600 mt-4">{result.contact}</div>}
    </div>
  )

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 mb-4">
      <h3 className="font-bold text-gray-800 mb-3">Verifiez et confirmez</h3>
      <div className="mb-4">
        {data.checklist?.documents?.filter((d: any) => d.status === 'ok').map((d: any, i: number) => (
          <div key={i} className="flex items-center gap-2 text-sm py-1">
            <span className="text-green-500">✓</span><span>{d.type}</span>
          </div>
        ))}
      </div>
      <div className="p-3 bg-orange-50 rounded-lg text-xs text-orange-700 mb-4">
        Votre carte grise sera envoyee a l'adresse figurant sur votre justificatif de domicile. Verifiez qu'elle est correcte.
      </div>
      <label className="flex gap-3 items-start cursor-pointer mb-4">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} className="mt-1 rounded" />
        <span className="text-sm text-gray-700">Je confirme l'envoi de mes documents a {data.commerce.nom || 'mon vendeur'} pour ma demande de carte grise.</span>
      </label>
      <button onClick={confirm} disabled={!checked || loading}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50">
        {loading ? 'Envoi...' : 'Envoyer mes documents'}
      </button>
    </div>
  )
}

function ClientTermine({ data }: { data: ClientPageData }) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-md">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">&#10003;</div>
          <h1 className="text-xl font-bold text-gray-800">{data.message}</h1>
        </div>
        {data.prochaines_etapes && (
          <div className="space-y-3 text-sm text-gray-600">
            {data.prochaines_etapes.map((e: any, i: number) => (
              <div key={i} className="flex gap-2"><span className="font-bold text-blue-600">{i + 1}.</span><span>{typeof e === 'string' ? e : e.description}</span></div>
            ))}
          </div>
        )}
        {data.contact && <div className="text-xs text-gray-400 mt-6 text-center">{data.contact}</div>}
      </div>
    </div>
  )
}
