import streamlit as st
import sqlite3
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
import sqlite3

# Initialisation automatique de la base de données et de la table projets
conn = sqlite3.connect("project_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS projets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase TEXT,
        statut TEXT,
        prix_vente REAL,
        prev_materiaux REAL,
        prev_moe REAL,
        prev_sous_traitance REAL,
        reel_materiaux REAL,
        reel_moe REAL,
        reel_sous_traitance REAL
    )
''')
conn.commit()
conn.close()
# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Gestion de Projet", layout="wide", page_icon="🏗️")

# --- DATABASE UTILITY FUNCTIONS ---
def run_query(query, params=()):
    conn = sqlite3.connect("project_data.db")
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_db_command(command, params=()):
    conn = sqlite3.connect("project_data.db")
    cursor = conn.cursor()
    cursor.execute(command, params)
    conn.commit()
    conn.close()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Compta-Analytique")
page = st.sidebar.radio(
    "Aller vers :",
    ["Vue d'ensemble", "Planning & Gantt", "Suivi Financier", "⚙️ Gestion des Projets"]
)
st.sidebar.markdown("---")
st.sidebar.info("Application connectée à SQLite (project_data.db)")

# Fetch project list globally for reusable dropdowns
df_global_projets = run_query("SELECT * FROM projets")

# ==========================================
# PAGE 1: VUE D'ENSEMBLE
# ==========================================
if page == "Vue d'ensemble":
    st.title("🏗️ Tableau de Bord — Données Réelles SQLite")
    st.write("Suivi global lu dynamiquement depuis la base de données locale.")
    
    total_projets = len(df_global_projets)
    total_portfolio_value = df_global_projets["prix_vente"].sum()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Projets Actifs en Base", value=str(total_projets))
    with col2:
        st.metric(label="Valeur Totale du Portefeuille (CA)", value=f"{total_portfolio_value:,.0f} €".replace(",", " "))
    with col3:
        st.metric(label="Statut Base de Données", value="Connecté", delta="Synchro OK")

    st.markdown("---")
    st.subheader("📋 Statut Général des Chantiers")
    if not df_global_projets.empty:
        df_summary = df_global_projets[['nom', 'phase', 'statut', 'prix_vente']].copy()
        df_summary.columns = ['Nom du Projet', 'Phase Actuelle', 'Statut', 'Prix de Vente (€)']
        st.dataframe(df_summary, use_container_width=True)
    else:
        st.info("Aucun projet en base de données. Allez dans l'onglet Gestion pour en créer un.")

# ==========================================
# PAGE 2: PLANNING & GANTT
# ==========================================
elif page == "Planning & Gantt":
    st.title("📅 Calendrier & Planning de Gantt Interactif")
    
    if not df_global_projets.empty:
        proj_mapping = dict(zip(df_global_projets['nom'], df_global_projets['id']))
        selected_proj_name = st.selectbox("Sélectionner un projet :", options=list(proj_mapping.keys()))
        selected_proj_id = proj_mapping[selected_proj_name]
        
        col_add, col_del = st.columns(2)
        
        with col_add:
            with st.expander("➕ Ajouter une nouvelle tâche au planning", expanded=False):
                new_task_name = st.text_input("Nom de la tâche (ex: Enrobés ou Grenaillage)")
                new_start = st.date_input("Date de début")
                new_finish = st.date_input("Date de fin")
                new_corps = st.selectbox("Corps d'état :", ["Gros Œuvre", "VRD", "Second Œuvre", "Électricité"])
                
                if st.button("Enregistrer la tâche"):
                    if new_task_name:
                        execute_db_command(
                            "INSERT INTO taches (projet_id, nom_tache, date_debut, date_fin, corps_etat) VALUES (?, ?, ?, ?, ?)",
                            (int(selected_proj_id), new_task_name, str(new_start), str(new_finish), new_corps)
                        )
                        st.success(f"Tâche '{new_task_name}' ajoutée !")
                        st.rerun()
                    else:
                        st.error("Veuillez entrer un nom de tâche.")

        with col_del:
            df_current_tasks = run_query("SELECT id, nom_tache FROM taches WHERE projet_id = ? OR projet_id = ?", params=(int(selected_proj_id), int(selected_proj_id)))
            with st.expander("🗑️ Supprimer une tâche existante", expanded=False):
                if not df_current_tasks.empty:
                    task_mapping = dict(zip(df_current_tasks['nom_tache'], df_current_tasks['id']))
                    task_to_delete = st.selectbox("Sélectionner la tâche à supprimer :", options=list(task_mapping.keys()))
                    
                    if st.button("Supprimer définitivement", type="primary"):
                        execute_db_command("DELETE FROM taches WHERE id = ?", params=(int(task_mapping[task_to_delete]),))
                        st.warning(f"Tâche '{task_to_delete}' supprimée.")
                        st.rerun()
                else:
                    st.info("Aucune tâche à supprimer pour le moment.")

        st.markdown("---")
        
        df_taches = run_query(
            "SELECT nom_tache as Task, date_debut as Start, date_fin as Finish, corps_etat as Resource FROM taches WHERE projet_id = ?",
            params=(int(selected_proj_id),)
        )
        
        if not df_taches.empty:
            fig = ff.create_gantt(df_taches, index_col='Resource', show_colorbar=True, group_tasks=True)
            fig.update_layout(xaxis=dict(type='date'))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_taches, use_container_width=True)
        else:
            st.info("Aucune tâche de planning enregistrée pour ce projet pour le moment.")
    else:
        st.info("Veuillez d'abord créer un projet dans l'onglet de gestion.")

# ==========================================
# PAGE 3: SUIVI FINANCIER
# ==========================================
elif page == "Suivi Financier":
    st.title("📊 Suivi Financier & Rentabilité Analytique")

    if not df_global_projets.empty:
        proj_mapping = dict(zip(df_global_projets['nom'], df_global_projets['id']))
        selected_proj_name = st.selectbox("Sélectionner le projet à analyser :", options=list(proj_mapping.keys()))
        
        p_data = df_global_projets[df_global_projets['nom'] == selected_proj_name].iloc[0]
        
        total_prev_cost = p_data['prev_materiaux'] + p_data['prev_moe'] + p_data['prev_sous_traitance']
        total_reel_cost = p_data['reel_materiaux'] + p_data['reel_moe'] + p_data['reel_sous_traitance']
        
        marge_prevue = p_data['prix_vente'] - total_prev_cost
        marge_reelle = p_data['prix_vente'] - total_reel_cost
        pct_marge_reelle = (marge_reelle / p_data['prix_vente'] * 100) if p_data['prix_vente'] > 0 else 0

        st.markdown("---")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(label="Prix de Vente (CA)", value=f"{p_data['prix_vente']:,.0f} €".replace(",", " "))
        with c2:
            st.metric(label="Coût Total Estimé", value=f"{total_prev_cost:,.0f} €".replace(",", " "))
        with c3:
            st.metric(label="Dépenses Réelles Totales", value=f"{total_reel_cost:,.0f} €".replace(",", " "), 
                      delta=f"Ecart: {total_reel_cost - total_prev_cost:,.0f} €".replace(",", " "), delta_color="inverse")
        with c4:
            st.metric(label="Marge Réelle Actuelle", value=f"{marge_reelle:,.0f} €".replace(",", " "), 
                      delta=f"{pct_marge_reelle:.1f}% du CA")

        st.markdown("---")
        col_chart, col_table = st.columns([3, 2])
        
        with col_chart:
            categories = ['Matériaux', 'Main d\'œuvre', 'Sous-traitance']
            prev_values = [p_data['prev_materiaux'], p_data['prev_moe'], p_data['prev_sous_traitance']]
            reel_values = [p_data['reel_materiaux'], p_data['reel_moe'], p_data['reel_sous_traitance']]
            
            fig_fin = go.Figure(data=[
                go.Bar(name='Chiffrage Initial', x=categories, y=prev_values, marker_color='#2ca02c'),
                go.Bar(name='Dépenses Réelles', x=categories, y=reel_values, marker_color='#d62728')
            ])
            fig_fin.update_layout(barmode='group', height=350, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_fin, use_container_width=True)

        with col_table:
            st.subheader("📋 Tableau Analytique des Écarts")
            fin_breakdown = {
                "Poste": ["Matériaux", "Main d'œuvre", "Sous-traitance", "TOTAL"],
                "Estimé (€)": [p_data['prev_materiaux'], p_data['prev_moe'], p_data['prev_sous_traitance'], total_prev_cost],
                "Réel (€)": [p_data['reel_materiaux'], p_data['reel_moe'], p_data['reel_sous_traitance'], total_reel_cost],
                "Écart (€)": [
                    p_data['reel_materiaux'] - p_data['prev_materiaux'],
                    p_data['reel_moe'] - p_data['prev_moe'],
                    p_data['reel_sous_traitance'] - p_data['prev_sous_traitance'],
                    total_reel_cost - total_prev_cost
                ]
            }
            df_fin_table = pd.DataFrame(fin_breakdown)
            st.dataframe(df_fin_table, use_container_width=True, hide_index=True)
            
            if total_reel_cost > total_prev_cost:
                st.error(f"⚠️ Alerte: Ce projet présente un dépassement budgétaire de {total_reel_cost - total_prev_cost:,.0f} € !".replace(",", " "))
            elif total_reel_cost > 0:
                st.success("✅ Maîtrise budgétaire: Les dépenses sont conformes ou inférieures aux prévisions.")
    else:
        st.info("Aucun projet disponible.")

# ==========================================
# PAGE 4: GESTION DES PROJETS (NEW OPERATIONAL WIZARD)
# ==========================================
elif page == "⚙️ Gestion des Projets":
    st.title("⚙️ Centre de Contrôle & Gestion Operational")
    st.write("Ajoutez de nouveaux chantiers ou modifiez instantanément les données financières en base.")
    
    tab_new, tab_edit = st.tabs(["➕ Créer un Nouveau Projet", "✏️ Modifier Budgets & Coûts Live"])
    
    # SUB-TAB 1: CREATE NEW PROJECT
    with tab_new:
        st.subheader("Création d'une nouvelle fiche affaire")
        with st.form("form_new_project", clear_on_submit=True):
            name = st.text_input("Nom de l'opération (ex: Extension Mairie)")
            phase = st.text_input("Phase actuelle (ex: Avant-projet / Exécution)")
            status = st.selectbox("Statut initial :", ["Planifié", "En Cours", "En Attente", "Terminé"])
            pv = st.number_input("Prix de Vente Contractuel (€)", min_value=0.0, step=5000.0)
            
            st.markdown("**Chiffrage Prévisionnel Initial :**")
            p_mat = st.number_input("Budget Prévisionnel Matériaux (€)", min_value=0.0, step=1000.0)
            p_moe = st.number_input("Budget Prévisionnel Main d'œuvre (€)", min_value=0.0, step=1000.0)
            p_st  = st.number_input("Budget Prévisionnel Sous-traitance (€)", min_value=0.0, step=1000.0)
            
            if st.form_submit_button("Créer le projet en base de données"):
                if name:
                    execute_db_command(
                        '''INSERT INTO projets (nom, phase, statut, prev_materiaux, prev_moe, prev_sous_traitance, prix_vente, reel_materiaux, reel_moe, reel_sous_traitance) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)''',
                        (name, phase, status, p_mat, p_moe, p_st, pv)
                    )
                    st.success(f"Projet '{name}' inséré avec succès en base de données ! 🎉")
                else:
                    st.error("Le nom du projet est obligatoire.")

    # SUB-TAB 2: EDIT EXISTING PROJECT LIVE
    with tab_edit:
        st.subheader("Mise à jour dynamique des postes comptables")
        if not df_global_projets.empty:
            proj_edit_mapping = dict(zip(df_global_projets['nom'], df_global_projets['id']))
            edit_proj_name = st.selectbox("Sélectionner le projet à modifier :", options=list(proj_edit_mapping.keys()), key="select_edit")
            
            # Extract row data
            e_data = df_global_projets[df_global_projets['nom'] == edit_proj_name].iloc[0]
            
            with st.form("form_edit_project"):
                st.write(f"Modifications en cours sur l'opération : **{edit_proj_name}**")
                
                up_phase = st.text_input("Phase actuelle", value=str(e_data['phase']))
                up_status = st.selectbox("Statut", ["Planifié", "En Cours", "En Attente", "Terminé"], index=["Planifié", "En Cours", "En Attente", "Terminé"].index(e_data['statut']))
                up_pv = st.number_input("Prix de Vente (€)", value=float(e_data['prix_vente']), step=1000.0)
                
                col_edit_prev, col_edit_reel = st.columns(2)
                
                with col_edit_prev:
                    st.markdown("🎯 **Ajuster le Chiffrage Estimé :**")
                    up_p_mat = st.number_input("Estimé Matériaux (€)", value=float(e_data['prev_materiaux']), step=500.0)
                    up_p_moe = st.number_input("Estimé Main d'œuvre (€)", value=float(e_data['prev_moe']), step=500.0)
                    up_p_st  = st.number_input("Estimé Sous-traitance (€)", value=float(e_data['prev_sous_traitance']), step=500.0)
                    
                with col_edit_reel:
                    st.markdown("💸 **Saisir les Dépenses Réelles Actuelles :**")
                    up_r_mat = st.number_input("Réel Matériaux (€)", value=float(e_data['reel_materiaux']), step=500.0)
                    up_r_moe = st.number_input("Réel Main d'œuvre (€)", value=float(e_data['reel_moe']), step=500.0)
                    up_r_st  = st.number_input("Réel Sous-traitance (€)", value=float(e_data['reel_sous_traitance']), step=500.0)
                
                if st.form_submit_button("Sauvegarder les modifications live"):
                    execute_db_command(
                        '''UPDATE projets SET phase=?, statut=?, prix_vente=?, prev_materiaux=?, prev_moe=?, prev_sous_traitance=?, 
                           reel_materiaux=?, reel_moe=?, reel_sous_traitance=? WHERE id=?''',
                        (up_phase, up_status, up_pv, up_p_mat, up_p_moe, up_p_st, up_r_mat, up_r_moe, up_r_st, int(e_data['id']))
                    )
                    st.success("Données enregistrées et calculées en base de données ! 🚀")
                    st.rerun()
        else:
            st.info("Aucun projet en base.")