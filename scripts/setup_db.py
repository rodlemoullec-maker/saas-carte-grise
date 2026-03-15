"""Création des tables PostgreSQL pour le projet Carte Grise Auto."""

import subprocess
import sys

SQL = """
-- Table des types mines (base technique véhicules ~500k entrées)
CREATE TABLE IF NOT EXISTS types_mines (
    cnit VARCHAR(20) PRIMARY KEY,
    marque VARCHAR(100),
    denomination_commerciale VARCHAR(200),
    genre VARCHAR(10),
    carrosserie VARCHAR(50),
    energie VARCHAR(10),
    cylindree INTEGER,
    puissance_fiscale INTEGER,
    puissance_kw NUMERIC(6,2),
    co2 INTEGER,
    nb_places INTEGER,
    poids_vide INTEGER,
    ptac INTEGER,
    date_debut DATE,
    date_fin DATE
);

-- Table des véhicules en stock
CREATE TABLE IF NOT EXISTS vehicules_stock (
    id SERIAL PRIMARY KEY,
    vin VARCHAR(17) UNIQUE NOT NULL,
    immatriculation VARCHAR(15),
    cnit VARCHAR(20) REFERENCES types_mines(cnit),
    marque VARCHAR(100),
    modele VARCHAR(200),
    date_premiere_immat DATE,
    km INTEGER,
    prix_vente NUMERIC(10,2),
    statut VARCHAR(20) DEFAULT 'en_stock',
    date_entree DATE,
    date_vente DATE
);

-- Table des dossiers carte grise
CREATE TABLE IF NOT EXISTS dossiers (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(20) UNIQUE NOT NULL,
    email_source VARCHAR(255),
    client_nom VARCHAR(200),
    client_email VARCHAR(255),
    immatriculation VARCHAR(15),
    vin VARCHAR(17),
    type_operation VARCHAR(50),
    region VARCHAR(50),
    statut VARCHAR(20) DEFAULT 'nouveau',
    donnees_extraites JSONB DEFAULT '{}',
    taxes JSONB DEFAULT '{}',
    cerfa_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des documents (pièces jointes)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    dossier_id INTEGER REFERENCES dossiers(id) ON DELETE CASCADE,
    type_document VARCHAR(50),
    fichier_path VARCHAR(500),
    donnees_json JSONB DEFAULT '{}',
    confidence FLOAT,
    ocr_texte_brut TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_types_mines_marque ON types_mines(marque);
CREATE INDEX IF NOT EXISTS idx_vehicules_stock_immat ON vehicules_stock(immatriculation);
CREATE INDEX IF NOT EXISTS idx_vehicules_stock_vin ON vehicules_stock(vin);
CREATE INDEX IF NOT EXISTS idx_dossiers_statut ON dossiers(statut);
CREATE INDEX IF NOT EXISTS idx_dossiers_reference ON dossiers(reference);
CREATE INDEX IF NOT EXISTS idx_dossiers_immat ON dossiers(immatriculation);
CREATE INDEX IF NOT EXISTS idx_documents_dossier ON documents(dossier_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type_document);

-- Fonction trigger pour updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger sur dossiers
DROP TRIGGER IF EXISTS trg_dossiers_updated_at ON dossiers;
CREATE TRIGGER trg_dossiers_updated_at
    BEFORE UPDATE ON dossiers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
"""


def main():
    # Essayer d'abord via SQLAlchemy (Docker / config .env)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from config.settings import DATABASE_URL
        from sqlalchemy import create_engine, text

        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            for statement in SQL.split(";"):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement + ";"))
            conn.commit()
        print("Tables créées avec succès (via SQLAlchemy).")
        return
    except Exception as e:
        print(f"SQLAlchemy non disponible ({e}), tentative via psql...")

    # Fallback : psql (dev local sans .env)
    result = subprocess.run(
        ["psql", "carte_grise", "-c", SQL],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERREUR: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Tables créées avec succès (via psql).")
    print(result.stdout)


if __name__ == "__main__":
    main()
