import { useState, useEffect } from 'react'

// Types
interface Dossier {
  id: string
  reference: string
  type: string
  vin: string | null
  immatriculation: string | null
  client_nom: string | null
  client_prenom: string | null
  status: string
  diagnostic: string | null
  blocages: any[]
  warnings: any[]
  tax_estimate: any | null
  phase0: any | null
  documents: DocItem[]
  created_at: string
}

interface DocItem {
  id: string
  filename: string
  type: string
  classification_confidence: number
  matched_keywords: string[]
  extracted_data: any
  status: string
}

const API = '/api'

// ─── Diagnostic Badge ────────────────────────────────────────────────────────

function DiagBadge({ diag }: { diag: string | null }) {
  if (!diag) return <span className="px-3 py-1 rounded-full text-sm bg-gray-200 text-gray-600">En attente</span>
  const colors: Record<string, string> = {
    VERT: 'bg-green-500 text-white',
    ORANGE: 'bg-orange-400 text-white',
    ROUGE: 'bg-red-500 text-white',
  }
  return <span className={`px-3 py-1 rounded-full text-sm font-bold ${colors[diag] || 'bg-gray-200'}`}>{diag}</span>
}

// ─── Home: Liste des dossiers ────────────────────────────────────────────────

function Home({ onSelect, onNew }: { onSelect: (id: string) => void; onNew: () => void }) {
  const [dossiers, setDossiers] = useState<Dossier[]>([])

  useEffect(() => {
    fetch(`${API}/dossiers`).then(r => r.json()).then(setDossiers)
  }, [])

  const counts = { VERT: 0, ORANGE: 0, ROUGE: 0, PENDING: 0 }
  dossiers.forEach(d => {
    const k = d.diagnostic || 'PENDING'
    counts[k as keyof typeof counts] = (counts[k as keyof typeof counts] || 0) + 1
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Carte Grise Pro</h1>
          <p className="text-gray-500 mt-1">Tableau de bord</p>
        </div>
        <button onClick={onNew} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium">
          + Nouveau dossier
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <div className="text-3xl font-bold text-green-600">{counts.VERT}</div>
          <div className="text-sm text-green-700">VERT</div>
        </div>
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 text-center">
          <div className="text-3xl font-bold text-orange-500">{counts.ORANGE}</div>
          <div className="text-sm text-orange-600">ORANGE</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
          <div className="text-3xl font-bold text-red-600">{counts.ROUGE}</div>
          <div className="text-sm text-red-700">ROUGE</div>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-3xl font-bold text-gray-500">{counts.PENDING}</div>
          <div className="text-sm text-gray-600">En attente</div>
        </div>
      </div>

      {/* List */}
      {dossiers.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-lg">Aucun dossier</p>
          <p className="text-sm mt-2">Cliquez sur "Nouveau dossier" pour commencer</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Reference</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Type</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Client</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">VIN / Immat</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Docs</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Diagnostic</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {dossiers.map(d => (
                <tr key={d.id} onClick={() => onSelect(d.id)} className="hover:bg-blue-50 cursor-pointer">
                  <td className="px-4 py-3 font-mono text-sm">{d.reference}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs font-medium ${d.type === 'VN' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>{d.type}</span></td>
                  <td className="px-4 py-3 text-sm">{d.client_nom} {d.client_prenom}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{d.vin || d.immatriculation || '—'}</td>
                  <td className="px-4 py-3 text-sm">{d.documents.length}</td>
                  <td className="px-4 py-3"><DiagBadge diag={d.diagnostic} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── New Dossier Form ────────────────────────────────────────────────────────

function NewDossier({ onCreated }: { onCreated: (id: string) => void }) {
  const [type, setType] = useState('VN')
  const [vin, setVin] = useState('')
  const [immat, setImmat] = useState('')
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [pm, setPm] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    const res = await fetch(`${API}/dossiers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type, vin: vin || null, immatriculation: immat || null,
        client_nom: nom || null, client_prenom: prenom || null,
        is_personne_morale: pm,
      }),
    })
    const data = await res.json()
    setLoading(false)
    onCreated(data.id)
  }

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-2xl font-bold mb-6">Nouveau dossier</h2>

      <div className="flex gap-4 mb-6">
        {['VN', 'VO'].map(t => (
          <button key={t} onClick={() => setType(t)}
            className={`flex-1 py-4 rounded-lg font-bold text-lg border-2 transition ${type === t ? (t === 'VN' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-purple-500 bg-purple-50 text-purple-700') : 'border-gray-200 text-gray-400'}`}>
            {t === 'VN' ? 'Vehicule Neuf' : 'Vehicule Occasion'}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {type === 'VN' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">VIN (17 caracteres)</label>
            <input value={vin} onChange={e => setVin(e.target.value.toUpperCase())} maxLength={17}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 font-mono" placeholder="VF1RFD00068123456" />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Immatriculation</label>
            <input value={immat} onChange={e => setImmat(e.target.value.toUpperCase())}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 font-mono" placeholder="AA-123-BB" />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom client</label>
            <input value={nom} onChange={e => setNom(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2" placeholder="DUPONT" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prenom</label>
            <input value={prenom} onChange={e => setPrenom(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2" placeholder="Jean" />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={pm} onChange={e => setPm(e.target.checked)} className="rounded" />
          Personne morale (societe)
        </label>
      </div>

      <button onClick={submit} disabled={loading}
        className="w-full mt-6 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50">
        {loading ? 'Creation...' : 'Creer le dossier'}
      </button>
    </div>
  )
}

// ─── Dossier Detail ──────────────────────────────────────────────────────────

function DossierView({ dossierId, onBack }: { dossierId: string; onBack: () => void }) {
  const [dossier, setDossier] = useState<Dossier | null>(null)
  const [uploading, setUploading] = useState(false)
  const [running, setRunning] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const reload = () => fetch(`${API}/dossiers/${dossierId}`).then(r => r.json()).then(setDossier)
  useEffect(() => { reload() }, [dossierId])

  const uploadFiles = async (files: FileList) => {
    setUploading(true)
    for (const file of Array.from(files)) {
      const form = new FormData()
      form.append('file', file)
      await fetch(`${API}/dossiers/${dossierId}/upload`, { method: 'POST', body: form })
    }
    setUploading(false)
    reload()
  }

  const runPipeline = async () => {
    setRunning(true)
    await fetch(`${API}/dossiers/${dossierId}/run-pipeline`, { method: 'POST' })
    setRunning(false)
    reload()
  }

  const downloadCerfa = () => {
    window.open(`${API}/dossiers/${dossierId}/cerfa`, '_blank')
  }

  if (!dossier) return <div className="text-center py-20 text-gray-400">Chargement...</div>

  return (
    <div>
      <button onClick={onBack} className="text-blue-600 hover:text-blue-800 mb-4 text-sm">&larr; Retour</button>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">{dossier.reference}</h2>
          <p className="text-gray-500 text-sm">
            <span className={`font-medium ${dossier.type === 'VN' ? 'text-blue-600' : 'text-purple-600'}`}>{dossier.type === 'VN' ? 'Vehicule Neuf' : 'Vehicule Occasion'}</span>
            {dossier.client_nom && <> &middot; {dossier.client_nom} {dossier.client_prenom}</>}
            {(dossier.vin || dossier.immatriculation) && <> &middot; <span className="font-mono">{dossier.vin || dossier.immatriculation}</span></>}
          </p>
        </div>
        <DiagBadge diag={dossier.diagnostic} />
      </div>

      {/* Phase 0 */}
      {dossier.phase0 && (
        <div className={`mb-6 p-4 rounded-lg border ${dossier.phase0.verdict === 'GO' ? 'bg-green-50 border-green-200' : dossier.phase0.verdict === 'WARNING' ? 'bg-orange-50 border-orange-200' : 'bg-red-50 border-red-200'}`}>
          <div className="font-bold text-sm mb-1">Phase 0 — HistoVec : {dossier.phase0.verdict}</div>
          {dossier.phase0.blockers?.map((b: string, i: number) => <div key={i} className="text-sm text-red-700">&#10005; {b}</div>)}
          {dossier.phase0.warnings?.map((w: string, i: number) => <div key={i} className="text-sm text-orange-600">&#9888; {w}</div>)}
          {dossier.phase0.verdict === 'GO' && <div className="text-sm text-green-700">&#10003; Aucun blocage SIV detecte</div>}
        </div>
      )}

      {/* Upload zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); uploadFiles(e.dataTransfer.files) }}
        className={`border-2 border-dashed rounded-lg p-8 text-center mb-6 transition ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300'}`}>
        <p className="text-gray-500 mb-2">{uploading ? 'Upload en cours...' : 'Glissez vos documents ici'}</p>
        <input type="file" multiple onChange={e => e.target.files && uploadFiles(e.target.files)}
          className="hidden" id="file-input" />
        <label htmlFor="file-input" className="text-blue-600 hover:text-blue-800 cursor-pointer text-sm">
          ou cliquez pour selectionner
        </label>
        <p className="text-xs text-gray-400 mt-2">PDF, JPG, PNG — 10 MB max par fichier</p>
      </div>

      {/* Documents list */}
      {dossier.documents.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-4 py-3 border-b bg-gray-50 font-medium text-sm text-gray-600">
            {dossier.documents.length} document(s) uploade(s)
          </div>
          {dossier.documents.map(doc => (
            <div key={doc.id} className="px-4 py-3 border-b last:border-0 flex items-center justify-between">
              <div>
                <span className="text-sm font-medium">{doc.filename}</span>
                <span className="ml-2 px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600">{doc.type}</span>
                <span className="ml-2 text-xs text-gray-400">confiance: {Math.round(doc.classification_confidence * 100)}%</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${doc.status === 'EXTRACTED' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                {doc.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Run pipeline button */}
      {dossier.documents.length > 0 && (
        <button onClick={runPipeline} disabled={running}
          className="w-full mb-6 bg-gray-900 hover:bg-gray-800 text-white py-3 rounded-lg font-medium disabled:opacity-50">
          {running ? 'Analyse en cours...' : 'Lancer le diagnostic Phase 1'}
        </button>
      )}

      {/* Diagnostic results */}
      {dossier.diagnostic && (
        <div className="space-y-6">
          {/* Blocages */}
          {dossier.blocages && dossier.blocages.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="font-bold text-red-800 mb-2">Blocages ({dossier.blocages.length})</h3>
              {dossier.blocages.map((b: any, i: number) => (
                <div key={i} className="text-sm text-red-700 mb-2 flex gap-2">
                  <span className="shrink-0">&#10005;</span>
                  <div>
                    <span className="font-mono text-xs bg-red-100 px-1 rounded">{b.code}</span>
                    <span className="ml-2">{b.message}</span>
                    {b.correction && <div className="text-xs text-red-500 mt-0.5">Action : {b.correction}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Warnings */}
          {dossier.warnings && dossier.warnings.length > 0 && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <h3 className="font-bold text-orange-700 mb-2">Avertissements ({dossier.warnings.length})</h3>
              {dossier.warnings.map((w: any, i: number) => (
                <div key={i} className="text-sm text-orange-600 mb-1 flex gap-2">
                  <span className="shrink-0">&#9888;</span>
                  <span>{w.message || w.code || JSON.stringify(w)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Tax estimate */}
          {dossier.tax_estimate && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-bold text-gray-800 mb-3">Estimation des taxes (indicatif)</h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between"><span>Y1 — Taxe regionale</span><span className="font-mono">{dossier.tax_estimate.y1_taxe_regionale?.toFixed(2) || '—'} EUR</span></div>
                <div className="flex justify-between"><span>Y3 — Malus CO2</span><span className="font-mono">{dossier.tax_estimate.y3_malus_co2?.toFixed(2) || '—'} EUR</span></div>
                <div className="flex justify-between"><span>Y4 — Taxe gestion</span><span className="font-mono">{dossier.tax_estimate.y4_taxe_gestion?.toFixed(2) || '—'} EUR</span></div>
                <div className="flex justify-between"><span>Y5 — Redevance</span><span className="font-mono">{dossier.tax_estimate.y5_redevance?.toFixed(2) || '—'} EUR</span></div>
                <div className="flex justify-between"><span>Y6 — Malus poids</span><span className="font-mono">{dossier.tax_estimate.y6_malus_poids?.toFixed(2) || '—'} EUR</span></div>
                <div className="flex justify-between border-t pt-1 font-bold"><span>Total estime</span><span className="font-mono">{dossier.tax_estimate.total?.toFixed(2) || '—'} EUR</span></div>
              </div>
              <p className="text-xs text-gray-400 mt-2">Montant final confirme par le SIV a la soumission</p>
            </div>
          )}

          {/* Infos (ce qui est OK) */}
          {(dossier as any).infos && (dossier as any).infos.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-bold text-green-700 mb-2">Verifications OK ({(dossier as any).infos.length})</h3>
              {(dossier as any).infos.map((info: any, i: number) => (
                <div key={i} className="text-sm text-green-600 mb-1 flex gap-2">
                  <span className="shrink-0">&#10003;</span>
                  <span>{info.message}</span>
                </div>
              ))}
            </div>
          )}

          {/* Cerfa button — visible seulement si VERT ou ORANGE */}
          {dossier.diagnostic !== 'ROUGE' && (
            <button onClick={downloadCerfa}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium">
              Generer Cerfa pre-rempli
            </button>
          )}
          {dossier.diagnostic === 'ROUGE' && (
            <div className="text-center text-sm text-gray-400 py-3">
              Corrigez les blocages ci-dessus pour generer le Cerfa
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Main App ────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState<'home' | 'new' | 'dossier'>('home')
  const [selectedId, setSelectedId] = useState<string>('')

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-4xl mx-auto py-8 px-4">
        {page === 'home' && (
          <Home
            onSelect={id => { setSelectedId(id); setPage('dossier') }}
            onNew={() => setPage('new')}
          />
        )}
        {page === 'new' && (
          <NewDossier onCreated={id => { setSelectedId(id); setPage('dossier') }} />
        )}
        {page === 'dossier' && (
          <DossierView dossierId={selectedId} onBack={() => setPage('home')} />
        )}
      </div>
    </div>
  )
}
