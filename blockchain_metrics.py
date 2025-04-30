import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from web3 import Web3
import os
import json

class BlockchainMetrics:
    """
    Classe pour collecter et analyser les métriques de performance de la blockchain
    """
    def __init__(self, blockchain_bridge):
        self.bridge = blockchain_bridge
        self.web3 = blockchain_bridge.web3 if blockchain_bridge else None
        
        # Métriques de performance des transactions
        self.transaction_times = {
            'register_agent': [],
            'allocate_energy': [],
            'advance_hour': [],
            'process_payment': []
        }
        
        # Consommation de gaz par type d'opération
        self.gas_usage = {
            'register_agent': [],
            'allocate_energy': [],
            'advance_hour': [],
            'process_payment': []
        }
        
        # Événements blockchain - vérifiez que ces noms correspondent exactement à ceux du contrat
        self.events = {
            'AgentRegistered': [],
            'EnergyAllocated': [],
            'HourAdvanced': [],
            'PriceUpdated': [],
            'EnergyCostCalculated': [],
            'PaymentProcessed': [],
            'ResourcesUpdated': []
        }
        
        # Taille de la blockchain
        self.blockchain_size = []
        self.block_info = []
        self.start_block = 0
        self.end_block = 0
        
        # Métriques économiques
        self.agent_costs = {}
        self.agent_benefits = {}
        
        # Métriques d'interaction
        self.interaction_matrix = None
        self.agent_names = []
        
        # Taux d'échec des transactions
        self.transaction_success = {
            'register_agent': {'success': 0, 'failed': 0},
            'allocate_energy': {'success': 0, 'failed': 0},
            'advance_hour': {'success': 0, 'failed': 0},
            'process_payment': {'success': 0, 'failed': 0}
        }
        
        # Coûts horaires (initialisé comme None, sera défini plus tard)
        self.hourly_costs = None
    
    def measure_transaction(self, tx_type, function_call):
        """
        Mesure le temps d'exécution et la consommation de gaz d'une transaction
        
        Args:
            tx_type (str): Type de transaction
            function_call: Fonction à appeler qui renvoie un hash de transaction
            
        Returns:
            receipt: Reçu de la transaction
        """
        if not self.web3:
            return None
            
        try:
            # Mesurer le temps
            start_time = time.time()
            
            # Exécuter la transaction
            tx_hash = function_call()
            
            # Attendre la confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Calculer le temps de confirmation
            confirmation_time = time.time() - start_time
            
            # Enregistrer les métriques
            self.transaction_times[tx_type].append(confirmation_time)
            self.gas_usage[tx_type].append(receipt['gasUsed'])
            self.transaction_success[tx_type]['success'] += 1
            
            return receipt
        except Exception as e:
            print(f"Erreur lors de la mesure de la transaction {tx_type}: {e}")
            self.transaction_success[tx_type]['failed'] += 1
            return None
    
    def update_blockchain_size(self):
        """
        Met à jour les informations sur la taille de la blockchain
        """
        if not self.web3:
            return
            
        try:
            current_block = self.web3.eth.block_number
            self.end_block = current_block
            
            if self.start_block == 0:
                self.start_block = current_block
            
            # Collecter les informations sur les blocs récents
            for block_num in range(max(self.end_block-5, self.start_block), self.end_block+1):
                try:
                    # Obtenir le bloc
                    block = self.web3.eth.get_block(block_num)
                    
                    # Convertir l'objet AttributeDict en dictionnaire standard
                    block_dict = {}
                    for key in dict(block).keys():
                        value = block[key]
                        # Convertir récursivement les AttributeDict imbriqués
                        if hasattr(value, 'items'):  # Si c'est un dict-like
                            value = dict(value)
                        block_dict[key] = value
                    
                    # Estimer la taille du bloc
                    try:
                        block_hex_raw = self.web3.toHex(block_num)
                        block_size = len(block_hex_raw) // 2
                    except Exception:
                        # Fallback si la conversion échoue
                        block_size = 1024  # Taille standard estimée
                    
                    # Ajouter les infos du bloc à notre liste
                    self.block_info.append({
                        'block_number': block_num,
                        'timestamp': block_dict.get('timestamp', 0),
                        'transactions': len(block_dict.get('transactions', [])),
                        'gas_used': block_dict.get('gasUsed', 0),
                        'gas_limit': block_dict.get('gasLimit', 0),
                        'size': block_size
                    })
                except Exception as e:
                    print(f"Erreur lors de la récupération du bloc {block_num}: {e}")
                    continue
            
            # Calculer la taille approximative de la blockchain
            total_size = sum(info.get('size', 0) for info in self.block_info)
            self.blockchain_size.append({
                'block': current_block,
                'size': total_size
            })
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la taille de la blockchain: {e}")

    def collect_events(self, from_block=None, to_block=None):
        """
        Collecte les événements de la blockchain - version robuste et compatible
        
        Args:
            from_block: Bloc de départ
            to_block: Bloc de fin
        """
        if not self.bridge or not self.bridge.contract:
            print("Pas de contrat disponible pour collecter des événements")
            return
            
        if from_block is None:
            from_block = self.start_block
        if to_block is None:
            to_block = self.end_block
            
        # Vérifier que les blocs sont bien spécifiés
        if from_block is None or to_block is None:
            print(f"Blocs mal spécifiés: from_block={from_block}, to_block={to_block}")
            return
        
        print(f"Collecte des événements du bloc {from_block} au bloc {to_block}")
        
        try:
            # Approche 1: Récupérer tous les logs de l'adresse du contrat
            all_logs = self.web3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': to_block,
                'address': self.bridge.contract.address
            })
            
            print(f"Total des logs récupérés: {len(all_logs)}")
            
            # Stocker tous les logs non triés pour référence
            self.events['ALL_LOGS'] = all_logs
            
            # Pour chaque type d'événement, filtrer les logs en utilisant la signature d'événement
            for event_name in self.events.keys():
                if event_name == 'ALL_LOGS':
                    continue  # Ignore la clé spéciale
                    
                try:
                    # Récupérer l'objet événement du contrat
                    event_obj = getattr(self.bridge.contract.events, event_name)
                    if event_obj:
                        # Utiliser get_logs avec un filtre spécifique à l'événement
                        event_filter = self.web3.eth.filter({
                            'fromBlock': from_block,
                            'toBlock': to_block,
                            'address': self.bridge.contract.address,
                            'topics': [event_obj().topic]  # Signature de l'événement
                        })
                        
                        event_logs = self.web3.eth.get_filter_logs(event_filter.filter_id)
                        
                        # Traiter les logs pour les convertir en format d'événement
                        processed_logs = []
                        for log in event_logs:
                            try:
                                processed_log = event_obj().process_log(log)
                                processed_logs.append(processed_log)
                            except Exception as e:
                                print(f"Erreur dans le traitement du log: {e}")
                        
                        self.events[event_name] = processed_logs
                        print(f"Récupéré {len(processed_logs)} événements {event_name}")
                        
                except Exception as e:
                    print(f"Impossible de filtrer les événements {event_name}: {e}")
            
        except Exception as e:
            print(f"Erreur générale lors de la collecte des événements: {e}")
            print(f"Exception détaillée: {str(e)}")
            
    def list_available_events(self):
        """Liste tous les événements disponibles dans le contrat"""
        if not self.bridge or not self.bridge.contract:
            print("Pas de contrat disponible")
            return []
        
        print("Événements disponibles dans le contrat:")
        available_events = []
        
        # Explorer tous les attributs de l'objet events
        for attr in dir(self.bridge.contract.events):
            # Ne pas inclure les méthodes internes/cachées
            if not attr.startswith('_'):
                available_events.append(attr)
                print(f" - {attr}")
        
        # Vérifier aussi les événements que vous essayez de collecter
        print("\nÉvénements que vous essayez de collecter:")
        for event_name in self.events.keys():
            if event_name != 'ALL_LOGS' and event_name in available_events:
                print(f" - {event_name} (DISPONIBLE)")
            elif event_name != 'ALL_LOGS':
                print(f" - {event_name} (NON DISPONIBLE)")
        
        return available_events
    
    def set_agent_data(self, agents, interactions):
        """
        Définit les données des agents pour les analyses
        
        Args:
            agents: Liste des agents
            interactions: Matrice d'interactions
        """
        self.agent_names = [agent.name for agent in agents]
        self.interaction_matrix = interactions
        
        # Collecter les coûts et bénéfices des agents
        for agent in agents:
            if hasattr(agent, 'total_cost'):
                self.agent_costs[agent.name] = abs(agent.total_cost) if agent.total_cost else 0
            if hasattr(agent, 'comfort'):
                self.agent_benefits[agent.name] = agent.comfort if agent.comfort is not None else 0
    
    def calculate_gini_coefficient(self):
        """
        Calcule le coefficient de Gini pour la distribution des coûts
        
        Returns:
            float: Coefficient de Gini (0 = parfaite égalité, 1 = inégalité maximale)
        """
        costs = list(self.agent_costs.values())
        if not costs or sum(costs) == 0:
            return 0
            
        costs = np.array(costs)
        n = len(costs)
        return np.sum(np.abs(np.subtract.outer(costs, costs))) / (2 * n * np.sum(costs))
    
    def calculate_cost_benefit_ratio(self):
        """
        Calcule le rapport coût/bénéfice pour chaque agent
        
        Returns:
            dict: Rapport coût/bénéfice par agent
        """
        ratio = {}
        for name in self.agent_costs.keys():
            cost = self.agent_costs.get(name, 0)
            benefit = self.agent_benefits.get(name, 0)
            if benefit > 0:
                ratio[name] = cost / benefit
            else:
                ratio[name] = cost  # Si pas de bénéfice, le rapport est juste le coût
        return ratio
    
    def calculate_transaction_statistics(self):
        """
        Calcule les statistiques des transactions
        
        Returns:
            dict: Statistiques des transactions
        """
        stats = {}
        for tx_type in self.transaction_times.keys():
            times = self.transaction_times[tx_type]
            gas = self.gas_usage[tx_type]
            
            if not times:
                stats[tx_type] = {
                    'avg_time': 0,
                    'min_time': 0,
                    'max_time': 0,
                    'avg_gas': 0,
                    'min_gas': 0,
                    'max_gas': 0,
                    'success_rate': 0
                }
                continue
                
            success = self.transaction_success[tx_type]['success']
            failed = self.transaction_success[tx_type]['failed']
            total = success + failed
            
            stats[tx_type] = {
                'avg_time': np.mean(times) if times else 0,
                'min_time': np.min(times) if times else 0,
                'max_time': np.max(times) if times else 0,
                'avg_gas': np.mean(gas) if gas else 0,
                'min_gas': np.min(gas) if gas else 0,
                'max_gas': np.max(gas) if gas else 0,
                'success_rate': success / total if total > 0 else 0
            }
        return stats
    
    def calculate_tps(self):
        """
        Calcule le nombre moyen de transactions par seconde
        
        Returns:
            float: Transactions par seconde
        """
        if not self.block_info:
            return 0
            
        total_transactions = sum(block['transactions'] for block in self.block_info)
        if len(self.block_info) < 2:
            return 0
            
        first_timestamp = self.block_info[0]['timestamp']
        last_timestamp = self.block_info[-1]['timestamp']
        duration = last_timestamp - first_timestamp
        
        if duration <= 0:
            return 0
            
        return total_transactions / duration
    
    def calculate_event_distribution(self):
        """
        Calcule la distribution des événements par type
        
        Returns:
            dict: Nombre d'événements par type
        """
        return {event_type: len(events) for event_type, events in self.events.items() if event_type != 'ALL_LOGS'}
    
    def generate_report(self):
        """
        Génère un rapport complet des métriques
        
        Returns:
            dict: Rapport des métriques
        """
        return {
            'transaction_stats': self.calculate_transaction_statistics(),
            'gini_coefficient': self.calculate_gini_coefficient(),
            'cost_benefit_ratio': self.calculate_cost_benefit_ratio(),
            'tps': self.calculate_tps(),
            'event_distribution': self.calculate_event_distribution(),
            'blockchain_size': self.blockchain_size[-1]['size'] if self.blockchain_size else 0,
            'agent_costs': self.agent_costs
        }
    
    def visualize_metrics(self, output_dir='.'):
        """
        Génère des visualisations des métriques
        
        Args:
            output_dir: Répertoire de sortie pour les graphiques
        """
        try:
            # Créer le répertoire s'il n'existe pas
            os.makedirs(output_dir, exist_ok=True)
            
            # 1. Performance des transactions
            self._plot_transaction_performance(output_dir)
            
            # 2. Consommation de gaz
            self._plot_gas_usage(output_dir)
            
            # 3. Distribution des coûts
            self._plot_cost_distribution(output_dir)
            
            # 4. Taux de succès des transactions
            self._plot_transaction_success_rate(output_dir)
            
            # 5. Distribution des événements
            self._plot_event_distribution(output_dir)
            
            # 6. Graphe des interactions
            self._plot_interaction_graph(output_dir)
            
            # 7. Heatmap des coûts horaires (si disponible)
            if hasattr(self, 'hourly_costs') and self.hourly_costs is not None and not self.hourly_costs.empty:
                self._plot_hourly_cost_heatmap(output_dir)
                
        except Exception as e:
            print(f"Erreur lors de la génération des visualisations: {e}")
    
    def _plot_transaction_performance(self, output_dir):
        """Visualisation de la performance des transactions"""
        try:
            stats = self.calculate_transaction_statistics()
            
            types = []
            avg_times = []
            
            for t, s in stats.items():
                if s['avg_time'] > 0:  # Ne montrer que les types de transactions utilisés
                    types.append(t)
                    avg_times.append(s['avg_time'])
            
            if not types:  # Si aucune transaction, ne pas créer de graphique
                return
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(types, avg_times)
            ax.set_xlabel('Type de transaction')
            ax.set_ylabel('Temps moyen (s)')
            ax.set_title('Temps moyen de confirmation par type de transaction')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/transaction_performance.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération du graphique de performance des transactions: {e}")
    
    def _plot_gas_usage(self, output_dir):
        """Visualisation de la consommation de gaz"""
        try:
            stats = self.calculate_transaction_statistics()
            
            types = []
            avg_gas = []
            
            for t, s in stats.items():
                if s['avg_gas'] > 0:  # Ne montrer que les types de transactions utilisés
                    types.append(t)
                    avg_gas.append(s['avg_gas'])
            
            if not types:  # Si aucune transaction, ne pas créer de graphique
                return
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(types, avg_gas)
            ax.set_xlabel('Type de transaction')
            ax.set_ylabel('Gaz moyen utilisé')
            ax.set_title('Consommation moyenne de gaz par type de transaction')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/gas_usage.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération du graphique de consommation de gaz: {e}")
    
    def _plot_cost_distribution(self, output_dir):
        """Visualisation de la distribution des coûts"""
        try:
            if not self.agent_costs:
                return
                
            names = []
            costs = []
            
            # Filtrer les agents avec coûts non nuls
            for name, cost in self.agent_costs.items():
                if cost > 0:
                    names.append(name)
                    costs.append(cost)
            
            if not names:  # Si aucun coût, ne pas créer de graphique
                return
            
            # Trier par coût
            sorted_idx = np.argsort(costs)
            names = [names[i] for i in sorted_idx]
            costs = [costs[i] for i in sorted_idx]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(names, costs)
            ax.set_xlabel('Agent')
            ax.set_ylabel('Coût ($)')
            ax.set_title(f'Distribution des coûts par agent (Gini: {self.calculate_gini_coefficient():.3f})')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/cost_distribution.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération du graphique de distribution des coûts: {e}")
    
    def _plot_transaction_success_rate(self, output_dir):
        """Visualisation du taux de succès des transactions"""
        try:
            success_rates = {}
            for tx_type, data in self.transaction_success.items():
                total = data['success'] + data['failed']
                if total > 0:  # Ne montrer que les types de transactions utilisés
                    success_rates[tx_type] = data['success'] / total
            
            if not success_rates:  # Si aucune transaction, ne pas créer de graphique
                return
            
            fig, ax = plt.subplots(figsize=(10, 6))
            types = list(success_rates.keys())
            rates = list(success_rates.values())
            
            ax.bar(types, rates)
            ax.set_xlabel('Type de transaction')
            ax.set_ylabel('Taux de succès')
            ax.set_title('Taux de succès des transactions par type')
            ax.set_ylim(0, 1.1)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/transaction_success_rate.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération du graphique de taux de succès des transactions: {e}")
    
    def _plot_event_distribution(self, output_dir):
        """Visualisation de la distribution des événements"""
        try:
            event_dist = self.calculate_event_distribution()
            
            # Vérifier si des événements ont été collectés
            total_events = sum(event_dist.values())
            if total_events == 0:
                print("Aucun événement collecté pour générer la distribution")
                # Créer un graphe vide avec un message
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, "Aucun événement collecté", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes, fontsize=14)
                ax.set_xlabel('Type d\'événement')
                ax.set_ylabel('Nombre d\'événements')
                ax.set_title('Distribution des événements blockchain')
                plt.savefig(f"{output_dir}/event_distribution.png")
                plt.close(fig)
                return
            
            # Ne garder que les événements avec au moins une occurrence
            types = []
            counts = []
            for event_type, count in event_dist.items():
                if count > 0 and event_type != 'ALL_LOGS':
                    types.append(event_type)
                    counts.append(count)
            
            if not types:  # Si aucun événement, ne pas créer de graphique
                return
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(types, counts)
            ax.set_xlabel('Type d\'événement')
            ax.set_ylabel('Nombre d\'événements')
            ax.set_title('Distribution des événements blockchain')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/event_distribution.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération du graphique de distribution des événements: {e}")
    
    def _plot_interaction_graph(self, output_dir):
        """Visualisation du graphe des interactions entre agents"""
        try:
            if self.interaction_matrix is None or not self.agent_names:
                return
                
            G = nx.DiGraph()
            
            # Ajouter les nœuds
            for name in self.agent_names:
                G.add_node(name)
            
            # Ajouter les arêtes (interactions)
            for i, from_agent in enumerate(self.agent_names):
                for j, to_agent in enumerate(self.agent_names):
                    if i < len(self.interaction_matrix) and j < len(self.interaction_matrix[i]):
                        if self.interaction_matrix[i, j] > 0:
                            G.add_edge(from_agent, to_agent, weight=self.interaction_matrix[i, j])
            
            if not G.edges():  # Si aucune interaction, ne pas créer de graphique
                return
            
            fig, ax = plt.subplots(figsize=(12, 10))
            pos = nx.spring_layout(G, seed=42)
            
            # Dessiner les nœuds
            nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=500, alpha=0.8)
            
            # Dessiner les arêtes avec des épaisseurs proportionnelles aux poids
            edges = G.edges()
            weights = [G[u][v]['weight'] for u, v in edges]
            max_weight = max(weights) if weights else 1
            normalized_weights = [w / max_weight * 5 for w in weights]
            
            nx.draw_networkx_edges(G, pos, width=normalized_weights, alpha=0.5, edge_color='gray', 
                                  connectionstyle='arc3,rad=0.1', arrowsize=15)
            
            # Ajouter les labels
            nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
            
            ax.set_title('Graphe des interactions entre agents')
            ax.axis('off')
            plt.tight_layout()
            plt.savefig(f"{output_dir}/interaction_graph.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération du graphe des interactions: {e}")
    
    def _plot_hourly_cost_heatmap(self, output_dir):
        """Visualisation de la heatmap des coûts horaires"""
        try:
            if self.hourly_costs is None or self.hourly_costs.empty:
                return
            
            # Convertir les données en valeurs numériques
            hourly_costs_numeric = self.hourly_costs.apply(pd.to_numeric, errors='coerce')
            
            fig, ax = plt.subplots(figsize=(12, 8))
            sns.heatmap(hourly_costs_numeric, cmap='YlOrRd', ax=ax)
            ax.set_xlabel('Heure')
            ax.set_ylabel('Agent')
            ax.set_title('Coûts énergétiques par heure et par agent')
            plt.tight_layout()
            plt.savefig(f"{output_dir}/hourly_cost_heatmap.png")
            plt.close(fig)
        except Exception as e:
            print(f"Erreur lors de la génération de la heatmap des coûts horaires: {e}")