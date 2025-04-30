import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import subprocess
import time
from pathlib import Path
import sys

# Assurez-vous que les modules du projet sont dans le path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import des modules du projet
# Import des modules du projet
from MAS import run_energy_management_with_blockchain
from blockchain_energy.src.blockchain_bridge import BlockchainBridge
from blockchain_metrics import BlockchainMetrics

# Configuration de Streamlit
st.set_page_config(
    page_title="Système Multi-Agents pour la Gestion d'Énergie Blockchain",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS personnalisé
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        background-color: #f0f2f6;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .metric-card {
        background-color: white;
        border-radius: 5px;
        padding: 15px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        text-align: center;
    }
    .big-number {
        font-size: 32px;
        font-weight: bold;
        color: #1E88E5;
    }
    .user-card {
        background-color: white;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .user-card h3 {
        color: #333;
        margin-top: 0;
    }
    .info-box {
        background-color: #e1f5fe;
        border-left: 5px solid #039be5;
        padding: 10px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .warning-box {
        background-color: #fff8e1;
        border-left: 5px solid #ffc107;
        padding: 10px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Fonction pour charger les données de coûts
def load_costs_data():
    try:
        # Charger les données des coûts variables pour les 24 heures
        C_grid_array = np.array([
            0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
            0.12, 0.12, 0.12, 0.12, 0.12, 0.12,
            0.12, 0.12, 0.12, 0.12, 0.12, 0.12,
            0.12, 0.12, 0.12, 0.12, 0.05, 0.05
        ])

        C_storage_array = np.array([
            0.35, 0.35, 0.35, 0.35, 0.35, 0.35,
            0.40, 0.40, 0.40, 0.40, 0.40, 0.40,
            0.40, 0.40, 0.40, 0.40, 0.40, 0.40,
            0.40, 0.40, 0.40, 0.40, 0.35, 0.35
        ])

        C_pv_array = np.array([
            0.10, 0.10, 0.10, 0.10, 0.10, 0.10,
            0.10, 0.10, 0.10, 0.10, 0.10, 0.10,
            0.10, 0.10, 0.10, 0.10, 0.10, 0.10,
            0.10, 0.10, 0.10, 0.10, 0.10, 0.10
        ])
        
        return {
            'grid': C_grid_array,
            'storage': C_storage_array,
            'pv': C_pv_array
        }
    except Exception as e:
        st.error(f"Erreur lors du chargement des données de coûts: {e}")
        return None

# Fonction pour charger les données de consommation
def load_consumption_data():
    try:
        # Création du DataFrame avec les données de consommation
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2019-06-10 00:00:00', periods=24, freq='h'),
            'conso_5RNS': [
                22.973739, 22.624288, 22.099875, 22.966455, 25.806568, 25.916713,
                26.147652, 27.465675, 23.325462, 24.638422, 28.049218, 28.175101,
                24.929978, 25.379126, 24.548666, 28.304361, 27.964538, 28.833112,
                24.124834, 27.444832, 23.589232, 21.945134, 19.556679, 19.946710
            ],
            'conso_HA': [
                46.386624, 45.930994, 45.682043, 45.923036, 47.151663, 48.719195,
                46.429420, 49.086484, 41.955689, 44.469950, 50.096358, 50.877831,
                44.879442, 45.830647, 42.930320, 49.306279, 49.072103, 52.395665,
                42.289834, 48.432067, 53.801493, 46.254925, 40.896865, 43.839718
            ],
            'conso_HEI': [
                82.232439, 80.643039, 80.482353, 79.082003, 86.633257, 89.308227,
                88.459662, 93.198944, 78.139266, 85.725691, 100.251738, 100.892304,
                89.149752, 93.522973, 88.439511, 102.448477, 98.329186, 96.956910,
                75.774048, 91.121469, 99.441998, 90.580749, 81.678680, 77.199761
            ],
            'conso_RIZOMME': [
                20.891538, 20.307705, 19.907527, 20.550549, 18.273802, 17.809438,
                18.241275, 19.887697, 16.579584, 18.568521, 21.602686, 20.054763,
                18.461463, 19.398784, 17.587338, 19.940883, 20.751782, 21.814314,
                17.811283, 21.758343, 23.167278, 20.652838, 17.895999, 19.013811
            ],
            'PV_total': [
                0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 1.20225, 3.81464,
                15.91954, 17.52773, 42.50442, 17.79276, 30.87777, 120.58479,
                100.33294, 138.16286, 120.93127, 130.83308, 80.03456, 40.43099,
                64.65445, 39.25586, 20.79903, 10.34629, 5.00000
            ]
        })
        
        return data
    except Exception as e:
        st.error(f"Erreur lors du chargement des données de consommation: {e}")
        return None

# Fonction pour charger les préférences des agents
def load_agent_preferences():
    try:
        # Préférences des différents agents
        preferences = {
            'building': [
                {'name': 'Building 1', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
                {'name': 'Building 2', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
                {'name': 'Building 3', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
                {'name': 'Building 4', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1}
            ],
            'EV': [
                {'name': 'EV 1', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
                {'name': 'EV 2', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
                {'name': 'EV 3', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
                {'name': 'EV 4', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
            ],
            'storage': [
                {'name': 'Storage', 'alpha': 0.8, 'beta': 0.2, 'gamma': 0.0}
            ],
            'PV': [
                {'name': 'PV', 'alpha': 0.8, 'beta': 0.1, 'gamma': 0.1},
            ]
        }
        
        return preferences
    except Exception as e:
        st.error(f"Erreur lors du chargement des préférences des agents: {e}")
        return None

# Fonction pour charger les caractéristiques des EVs
def load_ev_characteristics():
    try:
        ev_characteristics = [
            {'soc': 0.2, 'soc_required': 0.6, 'max_power': 22, 'eta': 0.8, 'arrival': 9, 'departure': 12, 'name': 'EV 1'},
            {'soc': 0.45, 'soc_required': 0.8, 'max_power': 22, 'eta': 0.8, 'arrival': 10, 'departure': 19, 'name': 'EV 2'},
            {'soc': 0.4, 'soc_required': 0.8, 'max_power': 7.2, 'eta': 0.8, 'arrival': 11, 'departure': 16, 'name': 'EV 3'},
            {'soc': 0.25, 'soc_required': 0.85, 'max_power': 22, 'eta': 0.8, 'arrival': 10, 'departure': 18, 'name': 'EV 4'},
        ]
        return ev_characteristics
    except Exception as e:
        st.error(f"Erreur lors du chargement des caractéristiques des véhicules électriques: {e}")
        return None

# Fonction pour charger les métriques blockchain
def load_blockchain_metrics(output_dir='blockchain_metrics'):
    try:
        report_path = os.path.join(output_dir, 'blockchain_metrics_report.json')
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                report = json.load(f)
            return report
        else:
            return None
    except Exception as e:
        st.error(f"Erreur lors du chargement des métriques blockchain: {e}")
        return None

# Fonction pour vérifier si Ganache est en cours d'exécution
def check_ganache_running():
    try:
        bridge = BlockchainBridge()
        return True
    except Exception:
        return False

# Fonction pour exécuter le modèle et retourner les résultats
def run_model(contract_address):
    try:
        # Créer un répertoire pour stocker les métriques
        os.makedirs('blockchain_metrics', exist_ok=True)
        
        # Exécuter le modèle avec l'adresse du contrat
        model, results_df = run_energy_management_with_blockchain(contract_address)
        
        return model, results_df
    except Exception as e:
        st.error(f"Erreur lors de l'exécution du modèle: {e}")
        return None, None

# Fonction pour exécuter le script de déploiement du contrat
def deploy_contract():
    try:
        # Chemin correct basé sur l'arborescence exacte
        deploy_script_path = os.path.join(current_dir, 'blockchain_energy', 'src', 'deploy.js')
        
        # Répertoire de travail pour le script
        working_dir = os.path.join(current_dir, 'blockchain_energy')
        
        # Exécuter le script de déploiement
        process = subprocess.Popen(
            ['node', 'src/deploy.js'],  # Utiliser le chemin relatif depuis working_dir
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            cwd=working_dir  # Définir le répertoire de travail
        )
        
        stdout, stderr = process.communicate()
        
        # Afficher la sortie complète pour le débogage
        st.write("Sortie standard:")
        st.code(stdout)
        
        st.write("Erreur standard:")
        st.code(stderr)
        
        if process.returncode != 0:
            st.error(f"Erreur lors du déploiement du contrat: {stderr}")
            return None
        
        # Extraire l'adresse du contrat de la sortie (en ignorant les problèmes d'encodage)
        for line in stdout.split('\n'):
            # Rechercher une adresse Ethereum (qui commence par 0x suivi de 40 caractères hexadécimaux)
            if "0x" in line:
                # Utiliser une expression régulière pour trouver l'adresse Ethereum
                import re
                matches = re.findall(r'0x[a-fA-F0-9]{40}', line)
                if matches:
                    return matches[0]  # Retourner la première adresse trouvée
        
        st.error("Impossible de trouver l'adresse du contrat dans la sortie")
        return None
    except Exception as e:
        st.error(f"Erreur lors du déploiement du contrat: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Fonction pour afficher les résultats de la simulation
def display_simulation_results(results_df):
    if results_df is None:
        st.warning("Aucun résultat de simulation disponible.")
        return
    
    st.subheader("Résultats de la Simulation")
    
    # Filtrer les lignes avec des valeurs Comfort non nulles
    results_with_comfort = results_df[results_df['Comfort'].notna()]
    
    # Calculer le confort moyen
    average_comfort = results_with_comfort['Comfort'].mean()
    
    # Calculer le coût total
    total_cost = results_df['Cost ($)'].sum()
    
    # Métriques clés
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p>Confort Moyen</p>
            <p class="big-number">{average_comfort:.2f}</p>
            <p>sur une échelle de 0 à 1</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <p>Coût Total</p>
            <p class="big-number">${abs(total_cost):.2f}</p>
            <p>pour tous les agents</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Afficher le tableau des résultats
    st.dataframe(results_df.style.format({
        'Cost ($)': '${:.2f}',
        'Comfort': '{:.2f}',
        'PV Used (kWh)': '{:.2f}'
    }), use_container_width=True)
    
    # Visualisation des coûts par agent
    st.subheader("Répartition des coûts par agent")
    
    # Créer un DataFrame filtré pour le graphique
    costs_df = results_df.copy()
    costs_df['Cost ($)'] = costs_df['Cost ($)'].abs()  # Valeur absolue pour l'affichage
    
    fig = px.bar(
        costs_df,
        x='User Name',
        y='Cost ($)',
        color='User Name',
        title="Coûts par Agent",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_layout(xaxis_title="Agent", yaxis_title="Coût ($)")
    st.plotly_chart(fig, use_container_width=True)
    
    # Visualisation du confort par agent
    st.subheader("Niveau de confort par agent")
    
    comfort_df = results_df[results_df['Comfort'].notna()].copy()
    
    fig = px.bar(
        comfort_df,
        x='User Name',
        y='Comfort',
        color='User Name',
        title="Confort par Agent",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_layout(xaxis_title="Agent", yaxis_title="Confort (0-1)")
    fig.update_yaxes(range=[0, 1])
    st.plotly_chart(fig, use_container_width=True)
    
    # Visualisation de l'utilisation du PV
    st.subheader("Utilisation de l'énergie PV par agent")
    
    pv_df = results_df[results_df['User Name'] != 'PV'].copy()  # Exclure l'agent PV lui-même
    
    fig = px.pie(
        pv_df,
        values='PV Used (kWh)',
        names='User Name',
        title="Répartition de l'utilisation de l'énergie PV",
        color_discrete_sequence=px.colors.sequential.Viridis
    )
    st.plotly_chart(fig, use_container_width=True)

# Fonction pour afficher les métriques blockchain
def display_blockchain_metrics(report, output_dir='blockchain_metrics'):
    if report is None:
        st.warning("Aucune métrique blockchain disponible. Exécutez d'abord la simulation.")
        return
    
    st.subheader("Métriques Blockchain")
    
    # Métriques clés
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <p>Coefficient de Gini</p>
            <p class="big-number">{report['gini_coefficient']:.4f}</p>
            <p>Distribution des coûts</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <p>Transactions par seconde</p>
            <p class="big-number">{report['tps']:.4f}</p>
            <p>TPS</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <p>Taille de la blockchain</p>
            <p class="big-number">{report['blockchain_size'] / 1024:.2f}</p>
            <p>KB</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Statistiques des transactions
    st.subheader("Performance des Transactions")
    
    tx_stats = []
    for tx_type, stats in report['transaction_stats'].items():
        if stats['avg_time'] > 0:  # Ne montrer que les types de transactions utilisés
            tx_stats.append({
                'Type': tx_type,
                'Temps moyen (s)': stats['avg_time'],
                'Gaz moyen': stats['avg_gas'],
                'Taux de succès (%)': stats['success_rate'] * 100
            })
    
    if tx_stats:
        tx_df = pd.DataFrame(tx_stats)
        
        # Afficher le tableau
        st.dataframe(tx_df.style.format({
            'Temps moyen (s)': '{:.4f}',
            'Gaz moyen': '{:.0f}',
            'Taux de succès (%)': '{:.1f}%'
        }), use_container_width=True)
        
        # Graphique de temps de transaction
        fig = px.bar(
            tx_df,
            x='Type',
            y='Temps moyen (s)',
            color='Type',
            title="Temps moyen de confirmation par type de transaction",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Graphique de consommation de gaz
        fig = px.bar(
            tx_df,
            x='Type',
            y='Gaz moyen',
            color='Type',
            title="Consommation moyenne de gaz par type de transaction",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune statistique de transaction disponible.")
    
    # Distribution des événements
    st.subheader("Distribution des Événements Blockchain")
    
    events = []
    for event_type, count in report['event_distribution'].items():
        if count > 0:
            events.append({
                'Type': event_type,
                'Nombre': count
            })
    
    if events:
        events_df = pd.DataFrame(events)
        
        fig = px.bar(
            events_df,
            x='Type',
            y='Nombre',
            color='Type',
            title="Distribution des événements blockchain",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun événement blockchain enregistré.")
    
    # Afficher les images générées (si disponibles)
    st.subheader("Visualisations")
    
    # Liste des visualisations possibles
    visualizations = [
        "transaction_performance.png",
        "gas_usage.png",
        "cost_distribution.png",
        "transaction_success_rate.png",
        "event_distribution.png",
        "interaction_graph.png",
        "hourly_cost_heatmap.png"
    ]
    
    cols = st.columns(2)
    for i, viz_file in enumerate(visualizations):
        viz_path = os.path.join(output_dir, viz_file)
        if os.path.exists(viz_path):
            # Alterner entre les colonnes
            with cols[i % 2]:
                st.image(viz_path, caption=viz_file.replace(".png", "").replace("_", " ").title())

# Fonction pour afficher les profils des agents
# Fonction pour afficher l'utilisation des ressources au fil du temps
def display_resource_usage_over_time(results_df, consumption_data):
    st.subheader("Répartition de l'utilisation des sources d'énergie au fil du temps")
    
    # Créer un DataFrame pour les sources à chaque heure
    hourly_data = []
    for hour in range(24):
        # Simuler la répartition des sources (à remplacer par les vraies données si disponibles)
        pv_available = consumption_data['PV_total'][hour]
        storage_used = min(40, pv_available * 0.3)  # Simulation
        grid_used = consumption_data[['conso_5RNS', 'conso_HA', 'conso_HEI', 'conso_RIZOMME']].sum(axis=1)[hour] - pv_available - storage_used
        
        hourly_data.append({
            'Heure': hour,
            'PV': pv_available if pv_available > 0 else 0,
            'Stockage': storage_used if storage_used > 0 else 0,
            'Réseau': max(0, grid_used)
        })
    
    df = pd.DataFrame(hourly_data)
    
    # Créer graphique d'aires empilées
    fig = px.area(df, x='Heure', y=['PV', 'Stockage', 'Réseau'],
                 title="Sources d'énergie utilisées par heure",
                 labels={'value': 'Énergie (kWh)', 'variable': 'Source'},
                 color_discrete_map={'PV': '#FFC107', 'Stockage': '#4CAF50', 'Réseau': '#2196F3'})
    
    fig.update_layout(legend_title="Source d'énergie", 
                     hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)

# Fonction pour afficher la heatmap des transactions blockchain
def display_blockchain_transaction_heatmap(report):
    st.subheader("Activité des transactions par type et par heure")
    
    # Créer des données simulées pour la démonstration
    hours = list(range(24))
    tx_types = ['register_agent', 'allocate_energy', 'advance_hour', 'process_payment']
    
    # Simuler l'activité des transactions (remplacer par les vraies données si disponibles)
    data = []
    for hour in hours:
        for tx_type in tx_types:
            # Générer une valeur simulée pour le nombre de transactions
            if tx_type == 'register_agent' and hour < 1:
                value = 10  # Beaucoup d'inscriptions au début
            elif tx_type == 'allocate_energy':
                value = 8 if 8 <= hour <= 18 else 3  # Plus d'allocations pendant la journée
            elif tx_type == 'advance_hour':
                value = 1  # Constant
            elif tx_type == 'process_payment':
                value = 0 if hour < 23 else 8  # Paiements à la fin
            
            data.append({
                'Heure': hour,
                'Type': tx_type,
                'Nombre': value
            })
    
    df = pd.DataFrame(data)
    
    # Créer une heatmap
    fig = px.density_heatmap(
        df, 
        x='Heure', 
        y='Type', 
        z='Nombre',
        title="Activité des transactions blockchain par heure",
        color_continuous_scale=px.colors.sequential.Viridis
    )
    
    fig.update_layout(
        xaxis_title="Heure du jour",
        yaxis_title="Type de transaction",
        coloraxis_colorbar=dict(title="Nombre de transactions")
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Fonction pour afficher le diagramme Sankey des flux d'énergie
def display_energy_flow_sankey(results_df, consumption_data):
    st.subheader("Flux d'énergie dans le système")
    
    # Calculer les valeurs totales (à remplacer par les vraies données si disponibles)
    total_pv = consumption_data['PV_total'].sum()
    total_grid = consumption_data[['conso_5RNS', 'conso_HA', 'conso_HEI', 'conso_RIZOMME']].sum().sum() - total_pv * 0.7
    total_storage_charge = total_pv * 0.3
    total_storage_discharge = total_storage_charge * 0.9  # Pertes dues à l'efficacité
    
    # Création des nœuds
    nodes = [
        {"name": "Production PV"},
        {"name": "Réseau électrique"},
        {"name": "Stockage"},
        {"name": "Bâtiment 1"},
        {"name": "Bâtiment 2"},
        {"name": "Bâtiment 3"},
        {"name": "Bâtiment 4"},
        {"name": "VE 1"},
        {"name": "VE 2"},
        {"name": "VE 3"},
        {"name": "VE 4"}
    ]
    
    # Création des liens entre les nœuds
    # [source, target, value]
    links = [
        # De PV à...
        {"source": 0, "target": 2, "value": total_pv * 0.3, "color": "#FFC107"},  # PV vers Stockage
        {"source": 0, "target": 3, "value": total_pv * 0.2, "color": "#FFC107"},  # PV vers Bâtiment 1
        {"source": 0, "target": 4, "value": total_pv * 0.2, "color": "#FFC107"},  # PV vers Bâtiment 2
        {"source": 0, "target": 5, "value": total_pv * 0.1, "color": "#FFC107"},  # PV vers Bâtiment 3
        {"source": 0, "target": 6, "value": total_pv * 0.1, "color": "#FFC107"},  # PV vers Bâtiment 4
        {"source": 0, "target": 7, "value": total_pv * 0.05, "color": "#FFC107"}, # PV vers VE 1
        {"source": 0, "target": 8, "value": total_pv * 0.05, "color": "#FFC107"}, # PV vers VE 2
        
        # Du réseau à...
        {"source": 1, "target": 3, "value": total_grid * 0.2, "color": "#2196F3"},  # Réseau vers Bâtiment 1
        {"source": 1, "target": 4, "value": total_grid * 0.2, "color": "#2196F3"},  # Réseau vers Bâtiment 2
        {"source": 1, "target": 5, "value": total_grid * 0.3, "color": "#2196F3"},  # Réseau vers Bâtiment 3
        {"source": 1, "target": 6, "value": total_grid * 0.1, "color": "#2196F3"},  # Réseau vers Bâtiment 4
        {"source": 1, "target": 7, "value": total_grid * 0.05, "color": "#2196F3"}, # Réseau vers VE 1
        {"source": 1, "target": 8, "value": total_grid * 0.05, "color": "#2196F3"}, # Réseau vers VE 2
        {"source": 1, "target": 9, "value": total_grid * 0.05, "color": "#2196F3"}, # Réseau vers VE 3
        {"source": 1, "target": 10, "value": total_grid * 0.05, "color": "#2196F3"}, # Réseau vers VE 4
        
        # Du stockage à...
        {"source": 2, "target": 5, "value": total_storage_discharge * 0.4, "color": "#4CAF50"},  # Stockage vers Bâtiment 3
        {"source": 2, "target": 6, "value": total_storage_discharge * 0.3, "color": "#4CAF50"},  # Stockage vers Bâtiment 4
        {"source": 2, "target": 9, "value": total_storage_discharge * 0.15, "color": "#4CAF50"}, # Stockage vers VE 3
        {"source": 2, "target": 10, "value": total_storage_discharge * 0.15, "color": "#4CAF50"}, # Stockage vers VE 4
    ]
    
    # Créer le diagramme Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=[node["name"] for node in nodes],
            color=["#FFC107", "#2196F3", "#4CAF50", "#9C27B0", "#9C27B0", "#9C27B0", "#9C27B0", 
                  "#FF5722", "#FF5722", "#FF5722", "#FF5722"]
        ),
        link=dict(
            source=[link["source"] for link in links],
            target=[link["target"] for link in links],
            value=[link["value"] for link in links],
            color=[link["color"] for link in links]
        )
    )])
    
    fig.update_layout(
        title="Flux d'énergie entre les agents",
        font=dict(size=12),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Fonction pour afficher le radar chart des performances des agents
def display_agent_performance_radar(results_df):
    st.subheader("Comparaison des performances des agents")
    
    # Filtrer pour n'avoir que les agents consommateurs
    consumer_agents = results_df[results_df['User Name'].str.contains('Building|EV')].copy()
    
    # Normaliser les valeurs pour le radar chart
    max_cost = consumer_agents['Cost ($)'].max()
    max_pv = consumer_agents['PV Used (kWh)'].max()
    
    # Calculer des métriques dérivées
    consumer_agents['Coût normalisé'] = 1 - (consumer_agents['Cost ($)'] / max_cost)  # Inversé pour que moins cher = meilleur
    consumer_agents['Utilisation PV'] = consumer_agents['PV Used (kWh)'] / max_pv
    consumer_agents['Confort'] = consumer_agents['Comfort']
    consumer_agents['Efficacité énergétique'] = consumer_agents['Utilisation PV'] * 0.7 + consumer_agents['Coût normalisé'] * 0.3
    
    # Créer un dataframe au format attendu par le radar chart
    radar_data = consumer_agents[['User Name', 'Coût normalisé', 'Utilisation PV', 'Confort', 'Efficacité énergétique']]
    
    # Créer le radar chart
    fig = go.Figure()
    
    for i, agent in radar_data.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[agent['Coût normalisé'], agent['Utilisation PV'], agent['Confort'], agent['Efficacité énergétique']],
            theta=['Coût', 'Utilisation PV', 'Confort', 'Efficacité'],
            fill='toself',
            name=agent['User Name']
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        title="Performance des agents consommateurs"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Fonction pour afficher la timeline des activités blockchain
def display_blockchain_timeline(report):
    st.subheader("Timeline des activités blockchain")
    
    # Simuler des événements blockchain avec des heures plus réalistes
    events = []
    
    # Date de base pour notre simulation (aujourd'hui)
    base_date = pd.Timestamp.now().floor('D')  # Aujourd'hui à minuit
    
    # Événements d'enregistrement des agents (au début)
    for i, agent_type in enumerate(["PV", "Storage", "Grid", "Building 1", "Building 2", "Building 3", "Building 4",
                                  "EV 1", "EV 2", "EV 3", "EV 4"]):
        events.append({
            "Agent": agent_type,
            "Événement": "Enregistrement",
            "Start": base_date + pd.Timedelta(minutes=i*5),  # Espacer les enregistrements de 5 minutes
            "End": base_date + pd.Timedelta(minutes=i*5 + 4),  # 4 minutes de durée
            "Gaz utilisé": 250000 + (i * 10000)
        })
    
    # Événements d'allocation d'énergie (pendant la journée)
    for hour in range(1, 24):
        hour_time = base_date + pd.Timedelta(hours=hour)
        
        for j, agent in enumerate(["Building 1", "Building 2", "Building 3", "Building 4"]):
            events.append({
                "Agent": agent,
                "Événement": "Allocation d'énergie",
                "Start": hour_time + pd.Timedelta(minutes=j*5),
                "End": hour_time + pd.Timedelta(minutes=j*5 + 3),
                "Gaz utilisé": 80000 + (hour * 100)
            })
        
        # EVs uniquement présents à certaines heures
        if 9 <= hour < 12:
            events.append({
                "Agent": "EV 1",
                "Événement": "Allocation d'énergie",
                "Start": hour_time + pd.Timedelta(minutes=20),
                "End": hour_time + pd.Timedelta(minutes=23),
                "Gaz utilisé": 75000 + (hour * 100)
            })
        if 10 <= hour < 19:
            events.append({
                "Agent": "EV 2",
                "Événement": "Allocation d'énergie",
                "Start": hour_time + pd.Timedelta(minutes=25),
                "End": hour_time + pd.Timedelta(minutes=28),
                "Gaz utilisé": 75000 + (hour * 100)
            })
        if 11 <= hour < 16:
            events.append({
                "Agent": "EV 3",
                "Événement": "Allocation d'énergie",
                "Start": hour_time + pd.Timedelta(minutes=30),
                "End": hour_time + pd.Timedelta(minutes=33),
                "Gaz utilisé": 75000 + (hour * 100)
            })
        if 10 <= hour < 18:
            events.append({
                "Agent": "EV 4",
                "Événement": "Allocation d'énergie",
                "Start": hour_time + pd.Timedelta(minutes=35),
                "End": hour_time + pd.Timedelta(minutes=38),
                "Gaz utilisé": 75000 + (hour * 100)
            })
    
    # Événements de paiement (à la fin)
    payment_time = base_date + pd.Timedelta(hours=23, minutes=45)
    for i, agent in enumerate(["Building 1", "Building 2", "Building 3", "Building 4", 
                              "EV 1", "EV 2", "EV 3", "EV 4"]):
        events.append({
            "Agent": agent,
            "Événement": "Paiement",
            "Start": payment_time + pd.Timedelta(minutes=i*2),
            "End": payment_time + pd.Timedelta(minutes=i*2 + 1.5),
            "Gaz utilisé": 120000 + (i * 5000)
        })
    
    # Créer un DataFrame
    events_df = pd.DataFrame(events)
    
    # Créer une figure Gantt avec des dates réalistes
    fig = px.timeline(
        events_df, 
        x_start="Start", 
        x_end="End",
        y="Agent",
        color="Événement",
        hover_data=["Gaz utilisé"],
        color_discrete_map={
            "Enregistrement": "#E91E63",
            "Allocation d'énergie": "#2196F3",
            "Paiement": "#4CAF50"
        }
    )
    
    fig.update_layout(
        title="Timeline des transactions blockchain",
        xaxis_title="Heure de la journée",
        yaxis_title="Agent",
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
def display_agent_profiles(agent_type):
    st.subheader(f"Profils des Agents {agent_type}")
    
    if agent_type == "Bâtiments":
        # Afficher les données pour les bâtiments
        consumption_data = load_consumption_data()
        building_prefs = load_agent_preferences()['building']
        
        for i, building in enumerate(building_prefs):
            with st.expander(f"{building['name']}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown(f"""
                    <div class="user-card">
                        <h3>{building['name']}</h3>
                        <p><b>Préférences d'approvisionnement:</b></p>
                        <ul>
                            <li>Réseau (α): {building['alpha']}</li>
                            <li>PV (β): {building['beta']}</li>
                            <li>Stockage (γ): {building['gamma']}</li>
                        </ul>
                        <p><b>Consommation totale:</b> {consumption_data[f'conso_{["5RNS", "HA", "HEI", "RIZOMME"][i]}'].sum():.2f} kWh</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Graphique de profil de consommation
                    fig = px.line(
                        x=list(range(24)),
                        y=consumption_data[f'conso_{["5RNS", "HA", "HEI", "RIZOMME"][i]}'],
                        title=f"Profil de Consommation - {building['name']}",
                        labels={'x': 'Heure', 'y': 'Consommation (kWh)'}
                    )
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
    
    elif agent_type == "Véhicules Électriques":
        # Afficher les données pour les EVs
        ev_characteristics = load_ev_characteristics()
        ev_prefs = load_agent_preferences()['EV']
        
        for i, ev in enumerate(ev_characteristics):
            with st.expander(f"{ev['name']}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown(f"""
                    <div class="user-card">
                        <h3>{ev['name']}</h3>
                        <p><b>Préférences d'approvisionnement:</b></p>
                        <ul>
                            <li>Réseau (α): {ev_prefs[i]['alpha']}</li>
                            <li>PV (β): {ev_prefs[i]['beta']}</li>
                            <li>Stockage (γ): {ev_prefs[i]['gamma']}</li>
                        </ul>
                        <p><b>Caractéristiques:</b></p>
                        <ul>
                            <li>SOC initiale: {ev['soc']}</li>
                            <li>SOC requise: {ev['soc_required']}</li>
                            <li>Puissance max: {ev['max_power']} kW</li>
                            <li>Efficacité: {ev['eta']}</li>
                        </ul>
                        <p><b>Plage de connexion:</b> {ev['arrival']}h - {ev['departure']}h</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Graphique de disponibilité
                    availability = [0] * 24
                    for h in range(ev['arrival'], ev['departure']):
                        availability[h] = 1
                    
                    fig = px.bar(
                        x=list(range(24)),
                        y=availability,
                        title=f"Disponibilité - {ev['name']}",
                        labels={'x': 'Heure', 'y': 'Disponible'},
                        color_discrete_sequence=['#4CAF50']
                    )
                    fig.update_layout(showlegend=False, yaxis=dict(tickvals=[0, 1], ticktext=['Non', 'Oui']))
                    st.plotly_chart(fig, use_container_width=True)
    
    elif agent_type == "Stockage":
        # Afficher les données pour le stockage
        storage_prefs = load_agent_preferences()['storage']
        
        with st.expander("Batterie de Stockage"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"""
                <div class="user-card">
                    <h3>Batterie de Stockage</h3>
                    <p><b>Préférences d'approvisionnement:</b></p>
                    <ul>
                        <li>Réseau (α): {storage_prefs[0]['alpha']}</li>
                        <li>PV (β): {storage_prefs[0]['beta']}</li>
                        <li>Stockage (γ): {storage_prefs[0]['gamma']}</li>
                    </ul>
                    <p><b>Caractéristiques:</b></p>
                    <ul>
                        <li>SOC initiale: 0.35</li>
                        <li>SOC minimale: 0.1</li>
                        <li>SOC maximale: 1.0</li>
                        <li>Puissance de charge: 40 kW</li>
                        <li>Puissance de décharge: 80 kW</li>
                        <li>Efficacité: 0.98</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Coûts horaires du stockage
                costs = load_costs_data()
                
                fig = px.line(
                    x=list(range(24)),
                    y=costs['storage'],
                    title="Coût du stockage par heure",
                    labels={'x': 'Heure', 'y': 'Coût ($/kWh)'},
                    color_discrete_sequence=['#FF9800']
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    
    elif agent_type == "PV":
        # Afficher les données pour le PV
        consumption_data = load_consumption_data()
        pv_prefs = load_agent_preferences()['PV']
        
        with st.expander("Production Photovoltaïque"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"""
                <div class="user-card">
                    <h3>Production PV</h3>
                    <p><b>Préférences:</b></p>
                    <ul>
                        <li>Réseau (α): {pv_prefs[0]['alpha']}</li>
                        <li>PV (β): {pv_prefs[0]['beta']}</li>
                        <li>Stockage (γ): {pv_prefs[0]['gamma']}</li>
                    </ul>
                    <p><b>Production totale:</b> {consumption_data['PV_total'].sum():.2f} kWh</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Graphique de production PV
                fig = px.line(
                    x=list(range(24)),
                    y=consumption_data['PV_total'],
                    title="Profil de Production PV",
                    labels={'x': 'Heure', 'y': 'Production (kWh)'},
                    color_discrete_sequence=['#FFC107']
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    
    elif agent_type == "Réseau":
        # Afficher les données pour le réseau
        costs = load_costs_data()
        
        with st.expander("Réseau Électrique"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("""
                <div class="user-card">
                    <h3>Réseau Électrique</h3>
                    <p><b>Caractéristiques:</b></p>
                    <ul>
                        <li>Puissance maximale: 580 kW</li>
                        <li>Tarification dynamique selon l'heure</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Graphique de coût du réseau
                fig = px.line(
                    x=list(range(24)),
                    y=costs['grid'],
                    title="Tarification du réseau par heure",
                    labels={'x': 'Heure', 'y': 'Coût ($/kWh)'},
                    color_discrete_sequence=['#E91E63']
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

# Afficher la page d'accueil
def display_home():
    st.title("Système Multi-Agents pour la Gestion d'Énergie avec Blockchain")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3>À propos de ce projet</h3>
            <p>Ce projet implémente un système de gestion d'énergie décentralisé basé sur la blockchain, utilisant une approche multi-agents pour optimiser la consommation et la distribution d'énergie dans une communauté.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        ### Fonctionnalités principales:
        - Simulation de la consommation et production d'énergie sur 24 heures
        - Intégration avec la blockchain Ethereum (Ganache) pour les transactions énergétiques
        - Différents types d'agents : Bâtiments, Véhicules électriques, Stockage, PV, Réseau
        - Analyse des métriques de performance blockchain
        - Métriques d'équité et d'efficacité énergétique
        """)
    
    with col2:
        st.markdown("""
        <div class="user-card">
            <h3>Composants du système</h3>
            <ul>
                <li>Agents consommateurs</li>
                <li>Agents producteurs</li>
                <li>Smart contracts</li>
                <li>Métriques blockchain</li>
                <li>Interface utilisateur</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.subheader("Répartition des agents dans le système")
    
    # Diagramme de la répartition des agents
    agent_counts = {
        'Bâtiments': 4,
        'Véhicules Électriques': 4,
        'Stockage': 1,
        'PV': 1,
        'Réseau': 1
    }
    
    fig = px.pie(
        values=list(agent_counts.values()),
        names=list(agent_counts.keys()),
        title="Répartition des agents dans le système",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Section de démarrage rapide
    st.subheader("Démarrage Rapide")
    
    ganache_running = check_ganache_running()
    
    if ganache_running:
        st.success("✅ Ganache est en cours d'exécution et accessible.")
    else:
        st.error("❌ Ganache n'est pas accessible. Veuillez démarrer Ganache avant de continuer.")
        st.markdown("""
        <div class="warning-box">
            <h4>Comment démarrer Ganache?</h4>
            <ol>
                <li>Installez Ganache depuis <a href='https://trufflesuite.com/ganache/' target='_blank'>le site officiel</a></li>
                <li>Lancez l'application Ganache</li>
                <li>Créez un nouveau workspace ou utilisez le workspace par défaut (quick start)</li>
                <li>Assurez-vous que Ganache est accessible à l'adresse <code>http://127.0.0.1:7545</code></li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Section pour déployer le contrat
    if ganache_running:
        st.subheader("Déployez le contrat intelligent")
        
        if st.button("Déployer le contrat EnergyManagementSystem"):
            with st.spinner("Déploiement du contrat en cours..."):
                contract_address = deploy_contract()
                if contract_address:
                    st.success(f"✅ Contrat déployé avec succès à l'adresse: {contract_address}")
                    st.session_state['contract_address'] = contract_address
                else:
                    st.error("❌ Échec du déploiement du contrat.")

# Application principale
def main():
    # Initialiser les variables de session si elles n'existent pas
    if 'contract_address' not in st.session_state:
        st.session_state['contract_address'] = None
    if 'model_run' not in st.session_state:
        st.session_state['model_run'] = False
    if 'results_df' not in st.session_state:
        st.session_state['results_df'] = None
    
    # Sidebar
    with st.sidebar:
        st.title("⚡ Gestion d'Énergie")
        
        # Section de configuration
        st.header("Configuration")
        
        # Afficher l'adresse du contrat actuel
        if st.session_state['contract_address']:
            st.success(f"Contrat actif: {st.session_state['contract_address']}")
        else:
            st.warning("Aucun contrat déployé. Veuillez d'abord déployer un contrat.")
        
        # Permettre à l'utilisateur d'entrer manuellement une adresse de contrat
        manual_address = st.text_input("Adresse du contrat (optionnel)", 
                                      value=st.session_state['contract_address'] if st.session_state['contract_address'] else "")
        if manual_address and manual_address != st.session_state['contract_address']:
            if manual_address.startswith("0x") and len(manual_address) == 42:
                st.session_state['contract_address'] = manual_address
                st.success(f"Adresse du contrat mise à jour: {manual_address}")
            else:
                st.error("Format d'adresse invalide. Une adresse Ethereum doit commencer par '0x' et avoir 42 caractères.")
        
        # Bouton pour exécuter la simulation
        if st.session_state['contract_address']:
            if st.button("🚀 Exécuter la simulation"):
                with st.spinner("Simulation en cours... Cela peut prendre quelques minutes."):
                    model, results_df = run_model(st.session_state['contract_address'])
                    if model and results_df is not None:
                        st.session_state['model_run'] = True
                        st.session_state['results_df'] = results_df
                        st.success("✅ Simulation terminée avec succès!")
                    else:
                        st.error("❌ Échec de la simulation.")
        
        st.divider()
        
        # Informations sur l'application
        st.markdown("""
        ### À propos
        Cette application permet de simuler et visualiser un système de gestion d'énergie basé sur la blockchain.
        
        Version: 1.0.0
        """)
    
    # Tabs de navigation principale
    tab_home, tab_agents, tab_simulation, tab_blockchain = st.tabs(["🏠 Accueil", "👥 Agents", "📊 Simulation", "🔗 Blockchain"])
    
    with tab_home:
        display_home()
    
    with tab_agents:
        st.title("Agents du Système")
        
        # Créer des tabs pour les différents types d'agents
        agent_tabs = st.tabs(["Bâtiments", "Véhicules Électriques", "Stockage", "PV", "Réseau"])
        
        with agent_tabs[0]:
            display_agent_profiles("Bâtiments")
        
        with agent_tabs[1]:
            display_agent_profiles("Véhicules Électriques")
        
        with agent_tabs[2]:
            display_agent_profiles("Stockage")
        
        with agent_tabs[3]:
            display_agent_profiles("PV")
        
        with agent_tabs[4]:
            display_agent_profiles("Réseau")
    
    with tab_simulation:
        st.title("Résultats de la Simulation")
        
        if st.session_state['model_run'] and st.session_state['results_df'] is not None:
            display_simulation_results(st.session_state['results_df'])
        else:
            st.info("Aucune simulation n'a encore été exécutée. Veuillez déployer un contrat et exécuter la simulation depuis le panneau latéral.")
            
            # Afficher un exemple de visualisation pour démonstration
            consumption_data = load_consumption_data()
            if consumption_data is not None:
                st.subheader("Exemple: Profils de consommation et production")
                
                # Créer un graphique pour tous les profils
                fig = go.Figure()
                
                # Ajouter les lignes de consommation
                fig.add_trace(go.Scatter(x=list(range(24)), y=consumption_data['conso_5RNS'], name='Building 1'))
                fig.add_trace(go.Scatter(x=list(range(24)), y=consumption_data['conso_HA'], name='Building 2'))
                fig.add_trace(go.Scatter(x=list(range(24)), y=consumption_data['conso_HEI'], name='Building 3'))
                fig.add_trace(go.Scatter(x=list(range(24)), y=consumption_data['conso_RIZOMME'], name='Building 4'))
                
                # Ajouter la ligne de production PV
                fig.add_trace(go.Scatter(x=list(range(24)), y=consumption_data['PV_total'], 
                                        name='Production PV', line=dict(color='gold', width=4)))
                
                fig.update_layout(
                    title="Profils de consommation et production",
                    xaxis_title="Heure",
                    yaxis_title="Puissance (kWh)",
                    legend_title="Agents",
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Message d'information
                st.markdown("""
                <div class="info-box">
                    <p>👆 Ce graphique montre les profils de consommation des bâtiments et la production PV disponible. 
                    Après l'exécution de la simulation, vous pourrez voir comment l'énergie est allouée entre les agents et les coûts associés.</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab_blockchain:
        st.title("Métriques Blockchain")
        
        # Charger les métriques blockchain si la simulation a été exécutée
        blockchain_metrics = load_blockchain_metrics() if st.session_state['model_run'] else None
        
        if blockchain_metrics:
            # Affichage des métriques existantes
            display_blockchain_metrics(blockchain_metrics)
            
            # Nouvelles visualisations
            st.markdown("---")
            st.header("Analyses blockchain supplémentaires")
            
            # Onglets pour les analyses blockchain supplémentaires
            blockchain_tabs = st.tabs(["Heatmap des transactions", "Timeline des activités"])
            
            with blockchain_tabs[0]:
                display_blockchain_transaction_heatmap(blockchain_metrics)
            
            with blockchain_tabs[1]:
                display_blockchain_timeline(blockchain_metrics)
        else:
            st.info("Aucune métrique blockchain disponible. Veuillez exécuter la simulation pour générer des métriques.")
            
            # Afficher un exemple de métriques pour démonstration
            st.subheader("Exemple: Transaction Gas Cost")
            
            # Créer des données d'exemple
            example_gas = pd.DataFrame({
                'Type': ['register_agent', 'allocate_energy', 'advance_hour', 'process_payment'],
                'Gas': [250000, 120000, 80000, 150000]
            })
            
            fig = px.bar(
                example_gas,
                x='Type',
                y='Gas',
                color='Type',
                title="Exemple: Consommation de gaz par type de transaction",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Message d'information
            st.markdown("""
            <div class="info-box">
                <p>👆 Ce graphique montre un exemple de consommation de gaz par type de transaction.
                Après l'exécution de la simulation, vous pourrez voir les métriques réelles de performance blockchain,
                la distribution des événements, et d'autres statistiques importantes.</p>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()