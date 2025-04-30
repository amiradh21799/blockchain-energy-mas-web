import numpy as np
import pandas as pd
import os
import json
from mesa import Agent, Model
from mesa.time import BaseScheduler
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
from blockchain_energy.src.blockchain_bridge import BlockchainBridge
from blockchain_metrics import BlockchainMetrics
import time

# =========================================================
# Données d'entrée
# =========================================================
# Coûts variables (24 valeurs, une par heure)
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

# Données de consommation et de production PV
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

# =========================================================
# Définition des Agents
# =========================================================

class BuildingAgent(Agent):
    def __init__(self, unique_id, model, demand_profile, preferences, name, blockchain_id=None):
        super().__init__(unique_id, model)
        self.demand_profile = demand_profile
        self.preferences = preferences
        self.name = name
        self.blockchain_id = blockchain_id  # ID de l'agent sur la blockchain
        
        self.consumed_from_pv = 0
        self.consumed_from_storage = 0
        self.consumed_from_grid = 0
        
        self.cost_pv = 0
        self.cost_storage = 0
        self.cost_grid = 0
        self.total_cost = 0
        
        self.pv_used = 0
        self.total_demand = sum(demand_profile)
        self.total_consumed = 0
        self.interactions = {}

    def interact(self, other_agent):
        self.interactions[other_agent.name] += 1
        other_agent.interactions[self.name] += 1

    def step(self):
        t = self.model.schedule.steps
        
        # Récupération des coûts variables pour l'heure t
        cost_grid_current = self.model.C_grid[t]
        cost_pv_current = self.model.C_pv[t]
        cost_storage_current = self.model.C_storage[t]

        demand = self.demand_profile[t]

        # Contribution PV
        pv_contribution = min(self.model.pv_agent.available_power * self.preferences['beta'], demand)
        self.consumed_from_pv = pv_contribution
        demand -= pv_contribution
        self.model.pv_agent.allocate_power(pv_contribution)

        # Contribution stockage
        storage_contribution = 0
        grid_contribution = 0

        if demand > 0 and self.model.storage_agent.soc > self.model.storage_agent.soc_min:
            storage_contribution = min(self.model.storage_agent.available_discharge_power * self.preferences['gamma'],
                                       demand)
            self.consumed_from_storage = storage_contribution
            demand -= storage_contribution
            self.model.storage_agent.discharge(storage_contribution)

        # Contribution réseau
        if demand > 0:
            grid_contribution = demand * self.preferences['alpha']
            self.consumed_from_grid = grid_contribution
            self.model.grid_agent.consume_power(grid_contribution)

        # Enregistrement des interactions
        self.interact(self.model.pv_agent)
        self.interact(self.model.storage_agent)
        self.interact(self.model.grid_agent)

        # Correction d'éventuels déséquilibres
        total_supply = self.consumed_from_pv + self.consumed_from_storage + self.consumed_from_grid
        total_demand = self.demand_profile[t]

        while not np.isclose(total_supply, total_demand, atol=1e-2):
            imbalance = total_supply - total_demand
            if imbalance > 0:  # Surproduction
                if self.consumed_from_storage > 0:
                    reduction = min(self.consumed_from_storage, imbalance)
                    self.consumed_from_storage -= reduction
                    imbalance -= reduction
                if imbalance > 0 and self.consumed_from_grid > 0:
                    self.consumed_from_grid = max(0, self.consumed_from_grid - imbalance)
            else:  # Sous-production
                additional_demand = -imbalance
                # Vérifie la limite de puissance max du grid
                if self.model.grid_agent.consumed_power + additional_demand <= self.model.grid_agent.max_power:
                    self.consumed_from_grid += additional_demand
                else:
                    max_grid_addition = self.model.grid_agent.max_power - self.consumed_from_grid
                    self.consumed_from_grid += max_grid_addition
                    self.consumed_from_storage += (additional_demand - max_grid_addition)

            # Recalcule supply et demand
            total_supply = self.consumed_from_pv + self.consumed_from_storage + self.consumed_from_grid
            total_demand = self.demand_profile[t]

        # S'assure que rien n'est négatif
        self.consumed_from_storage = max(0, self.consumed_from_storage)
        self.consumed_from_grid = max(0, self.consumed_from_grid)

        # Mise à jour consommation totale
        self.total_consumed += total_supply

        # Calcul des coûts (en fonction de l'heure)
        self.cost_pv = self.consumed_from_pv * cost_pv_current
        self.cost_storage = self.consumed_from_storage * cost_storage_current
        self.cost_grid = self.consumed_from_grid * cost_grid_current
        self.total_cost += self.cost_pv + self.cost_storage + self.cost_grid

        # PV utilisée
        self.pv_used += self.consumed_from_pv

        # Debug
        print(
            f"Hour {t}: {self.name} consumed {self.demand_profile[t]:.2f} kWh, "
            f"cost: ${-self.total_cost:.2f}, sources: {{"
            f"'PV': {self.consumed_from_pv:.2f} kWh (${self.cost_pv:.2f}), "
            f"'Storage': {self.consumed_from_storage:.2f} kWh (${self.cost_storage:.2f}), "
            f"'Grid': {self.consumed_from_grid:.2f} kWh (${self.cost_grid:.2f})}}"
        )
        
        # Envoi des données à la blockchain si un ID blockchain est défini
        if self.blockchain_id is not None and self.model.blockchain_bridge is not None:
            try:
                # Mise à jour des ressources disponibles
                self.model.blockchain_bridge.contract.functions.updateEnergySources(
                    int(self.model.pv_agent.available_power * 10**18),
                    int(self.model.storage_agent.available_discharge_power * 10**18)
                ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                
                # Allocation d'énergie pour le bâtiment avec mesure de performance
                print(f"DEBUG: Appel allocateBuildingEnergy avec ID blockchain {self.blockchain_id}")
                
                if self.model.blockchain_metrics:
                    def allocate_energy_call():
                        return self.model.blockchain_bridge.contract.functions.allocateBuildingEnergy(
                            self.blockchain_id
                        ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                    
                    receipt = self.model.blockchain_metrics.measure_transaction('allocate_energy', allocate_energy_call)
                else:
                    # Version originale sans métriques
                    self.model.blockchain_bridge.contract.functions.allocateBuildingEnergy(
                        self.blockchain_id
                    ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                
                print(f"Données envoyées à la blockchain pour {self.name}")
            except Exception as e:
                print(f"Erreur lors de l'envoi des données à la blockchain pour {self.name}: {e}")
                if self.model.blockchain_metrics:
                    self.model.blockchain_metrics.transaction_success['allocate_energy']['failed'] += 1

    def finalize(self):
        # Confort = ratio énergie reçue / énergie demandée
        self.comfort = self.total_consumed / self.total_demand if self.total_demand > 0 else 0
        
        # Traitement du paiement via blockchain si un ID blockchain est défini
        if self.blockchain_id is not None and self.model.blockchain_bridge is not None:
            try:
                # Récupération du coût total depuis la blockchain
                cost = self.model.blockchain_bridge.contract.functions.calculateTotalCost(
                    self.blockchain_id
                ).call()
                
                # Traitement du paiement
                account_index = self.blockchain_id + 1  # Premier compte pour propriétaire, autres pour agents
                
                if self.model.blockchain_metrics:
                    def process_payment_call():
                        return self.model.blockchain_bridge.contract.functions.processPayment(
                            self.blockchain_id, 0, cost
                        ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                    receipt = self.model.blockchain_metrics.measure_transaction('process_payment', process_payment_call)
                    if receipt:
                        print(f"Paiement effectué pour {self.name}, transaction: {receipt['transactionHash'].hex()}")
                else:
                    receipt = self.model.blockchain_bridge.process_payment(
                        self.blockchain_id, account_index
                    )
                    print(f"Paiement effectué pour {self.name}, transaction: {receipt.transactionHash.hex()}")
                
            except Exception as e:
                print(f"Erreur lors du traitement du paiement pour {self.name}: {e}")
                if self.model.blockchain_metrics:
                    self.model.blockchain_metrics.transaction_success['process_payment']['failed'] += 1


class EVAgent(Agent):
    def __init__(self, unique_id, model, soc, soc_required, max_power, eta, preferences, arrival, departure, name, blockchain_id=None):
        super().__init__(unique_id, model)
        self.soc = soc
        self.soc_required = soc_required
        self.soc_max = 1.0
        
        self.max_power = max_power
        self.eta = eta
        self.preferences = preferences
        
        self.arrival = arrival
        self.departure = departure
        self.name = name
        self.blockchain_id = blockchain_id  # ID de l'agent sur la blockchain
        
        self.consumed_from_pv = 0
        self.consumed_from_storage = 0
        self.consumed_from_grid = 0
        
        self.cost_pv = 0
        self.cost_storage = 0
        self.cost_grid = 0
        self.total_cost = 0
        
        self.pv_used = 0
        self.interactions = {}

    def interact(self, other_agent):
        self.interactions[other_agent.name] += 1
        other_agent.interactions[self.name] += 1

    def step(self):
        t = self.model.schedule.steps
        
        # Coûts variables pour l'heure t
        cost_grid_current = self.model.C_grid[t]
        cost_pv_current = self.model.C_pv[t]
        cost_storage_current = self.model.C_storage[t]
        
        # L'EV ne charge que pendant son intervalle d'arrivée/départ
        if self.arrival <= t < self.departure and self.soc < self.soc_required:
            # Besoin de charge
            demand = (self.soc_required - self.soc) * (self.max_power / self.eta)

            # PV
            pv_contribution = min(self.model.pv_agent.available_power * self.preferences['beta'], demand)
            self.soc += pv_contribution * self.eta
            self.soc = min(self.soc, self.soc_max)
            self.model.pv_agent.allocate_power(pv_contribution)
            demand -= pv_contribution

            # Stockage
            storage_contribution = 0
            if demand > 0 and self.model.storage_agent.soc > self.model.storage_agent.soc_min:
                storage_contribution = min(
                    self.model.storage_agent.available_discharge_power * self.preferences['gamma'],
                    demand
                )
                self.soc += storage_contribution * self.eta
                self.soc = min(self.soc, self.soc_max)
                self.model.storage_agent.discharge(storage_contribution)
                demand -= storage_contribution

            # Réseau
            grid_contribution = 0
            if demand > 0:
                grid_contribution = demand * self.preferences['alpha']
                self.soc += grid_contribution * self.eta
                self.soc = min(self.soc, self.soc_max)
                self.model.grid_agent.consume_power(grid_contribution)

            # Enregistrement des consommations
            self.consumed_from_pv = pv_contribution
            self.consumed_from_storage = storage_contribution
            self.consumed_from_grid = grid_contribution

            # Interactions
            self.interact(self.model.pv_agent)
            self.interact(self.model.storage_agent)
            self.interact(self.model.grid_agent)

            # Coûts
            self.cost_pv = self.consumed_from_pv * cost_pv_current
            self.cost_storage = self.consumed_from_storage * cost_storage_current
            self.cost_grid = self.consumed_from_grid * cost_grid_current
            self.total_cost += self.cost_pv + self.cost_storage + self.cost_grid

            # PV utilisée
            self.pv_used += self.consumed_from_pv

            print(
                f"Hour {t}: {self.name} charged, sources: "
                f"{{'PV': {pv_contribution:.2f} kWh (${self.cost_pv:.2f}), "
                f"'Storage': {storage_contribution:.2f} kWh (${self.cost_storage:.2f}), "
                f"'Grid': {grid_contribution:.2f} kWh (${self.cost_grid:.2f})}}"
            )
            
            # Envoi des données à la blockchain si un ID blockchain est défini
            if self.blockchain_id is not None and self.model.blockchain_bridge is not None:
                try:
                    # Mise à jour des ressources disponibles
                    self.model.blockchain_bridge.contract.functions.updateEnergySources(
                        int(self.model.pv_agent.available_power * 10**18),
                        int(self.model.storage_agent.available_discharge_power * 10**18)
                    ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                    
                    # Allocation d'énergie pour l'EV avec mesure de performance
                    print(f"DEBUG: Appel allocateEVEnergy avec ID blockchain {self.blockchain_id}")
                    
                    if self.model.blockchain_metrics:
                        def allocate_ev_energy_call():
                            return self.model.blockchain_bridge.contract.functions.allocateEVEnergy(
                                self.blockchain_id
                            ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                        
                        receipt = self.model.blockchain_metrics.measure_transaction('allocate_energy', allocate_ev_energy_call)
                    else:
                        # Version originale sans métriques
                        self.model.blockchain_bridge.contract.functions.allocateEVEnergy(
                            self.blockchain_id
                        ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                    
                    print(f"Données envoyées à la blockchain pour {self.name}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi des données à la blockchain pour {self.name}: {e}")
                    if self.model.blockchain_metrics:
                        self.model.blockchain_metrics.transaction_success['allocate_energy']['failed'] += 1

    def finalize(self):
        self.soc = min(self.soc, self.soc_max)
        self.comfort = self.soc / self.soc_max if self.soc_max > 0 else 0
        print(
            f"{self.name} final cost: ${-self.total_cost:.2f}, "
            f"comfort: {self.comfort:.2f}, PV used: {self.pv_used:.2f} kWh"
        )
        
        # Traitement du paiement via blockchain si un ID blockchain est défini
        if self.blockchain_id is not None and self.model.blockchain_bridge is not None:
            try:
                # Récupération du coût total depuis la blockchain
                cost = self.model.blockchain_bridge.contract.functions.calculateTotalCost(
                    self.blockchain_id
                ).call()
                
                # Traitement du paiement
                account_index = self.blockchain_id + 1  # Premier compte pour propriétaire, autres pour agents
                
                if self.model.blockchain_metrics:
                    def process_payment_call():
                        return self.model.blockchain_bridge.contract.functions.processPayment(
                            self.blockchain_id, 0, cost
                        ).transact({'from': self.model.blockchain_bridge.web3.eth.accounts[0], 'gas': 1000000})
                                        
                    receipt = self.model.blockchain_metrics.measure_transaction('process_payment', process_payment_call)
                    if receipt:
                        print(f"Paiement effectué pour {self.name}, transaction: {receipt['transactionHash'].hex()}")
                else:
                    receipt = self.model.blockchain_bridge.process_payment(
                        self.blockchain_id, account_index
                    )
                    print(f"Paiement effectué pour {self.name}, transaction: {receipt.transactionHash.hex()}")
                
            except Exception as e:
                print(f"Erreur lors du traitement du paiement pour {self.name}: {e}")
                if self.model.blockchain_metrics:
                    self.model.blockchain_metrics.transaction_success['process_payment']['failed'] += 1


class StorageAgent(Agent):
    def __init__(self, unique_id, model, soc, max_soc, min_soc, charge_power, discharge_power, efficiency, name, blockchain_id=None):
        super().__init__(unique_id, model)
        self.soc = soc
        self.max_soc = max_soc
        self.soc_min = min_soc
        
        self.charge_power = charge_power
        self.discharge_power = discharge_power
        self.efficiency = efficiency
        
        self.name = name
        self.blockchain_id = blockchain_id  # ID de l'agent sur la blockchain
        
        self.consumed_from_pv = 0
        self.consumed_from_grid = 0
        
        self.cost_pv = 0
        self.cost_grid = 0
        self.revenue_storage = 0
        
        self.total_cost = 0
        self.pv_used = 0
        self.interactions = {}

    def interact(self, other_agent):
        self.interactions[other_agent.name] += 1
        other_agent.interactions[self.name] += 1

    @property
    def available_discharge_power(self):
        # Puisance disponible à la décharge
        return min(self.discharge_power, (self.soc - self.soc_min) * self.efficiency)

    def discharge(self, power):
        self.soc = max(self.soc_min, self.soc - power / self.efficiency)
        # Le "gain" du stockage est calculé avec le même coût unitaire
        # Mais comme c'est un coût négatif pour l'agent, on l'additionne en "revenue"
        # (ça dépend de la convention adoptée)
        current_cost_storage = self.model.C_storage[self.model.schedule.steps]
        self.revenue_storage += power * current_cost_storage

    def step(self):
        t = self.model.schedule.steps
        # Coûts variables
        cost_grid_current = self.model.C_grid[t]
        cost_pv_current = self.model.C_pv[t]
        
        # Si on peut encore charger
        if self.soc < self.max_soc:
            charge_power = min(self.charge_power, (self.max_soc - self.soc) / self.efficiency)
            
            # Charge d'abord depuis le PV (s'il y a de la dispo)
            pv_contribution = min(self.model.pv_agent.available_power, charge_power)
            grid_contribution = charge_power - pv_contribution
            
            # Mise à jour de la SOC
            self.soc += pv_contribution * self.efficiency
            self.soc += grid_contribution * self.efficiency
            
            # PV allouée
            self.model.pv_agent.allocate_power(pv_contribution)
            
            # Enregistrement des consommations
            self.consumed_from_pv = pv_contribution
            self.consumed_from_grid = grid_contribution

            # Interactions
            self.interact(self.model.pv_agent)
            self.interact(self.model.grid_agent)

            # Coûts
            self.cost_pv = self.consumed_from_pv * cost_pv_current
            self.cost_grid = self.consumed_from_grid * cost_grid_current
            self.total_cost += self.cost_pv + self.cost_grid

            # PV utilisée
            self.pv_used += self.consumed_from_pv

            print(
                f"Hour {t}: {self.name} charged from PV with {pv_contribution:.2f} kWh, "
                f"cost: ${self.cost_pv:.2f}. SOC is now {self.soc:.2f}"
            )

    def finalize(self):
        # Coût net = coûts d'achat (total_cost) - revenu de décharge
        self.total_cost = self.total_cost - self.revenue_storage
        self.comfort = self.soc / self.max_soc if self.max_soc > 0 else 0


class PVAgent(Agent):
    def __init__(self, unique_id, model, power_profile, name, blockchain_id=None):
        super().__init__(unique_id, model)
        self.power_profile = power_profile
        self.available_power = 0
        
        self.revenue = 0
        self.energy_sold = 0
        
        self.name = name
        self.blockchain_id = blockchain_id  # ID de l'agent sur la blockchain
        self.interactions = {}

    def interact(self, other_agent):
        self.interactions[other_agent.name] += 1
        other_agent.interactions[self.name] += 1

    def allocate_power(self, power):
        # Coût (ou revenu pour le PV) : on utilise le coût PV à l'heure courante
        current_cost_pv = self.model.C_pv[self.model.schedule.steps]
        self.available_power = max(0, self.available_power - power)
        self.revenue += power * current_cost_pv
        self.energy_sold += power

    def step(self):
        t = self.model.schedule.steps
        self.available_power = self.power_profile[t]
        print(f"Hour {t}: {self.name} generated {self.available_power:.2f} kWh")

    def finalize(self):
        pass


class GridAgent(Agent):
    def __init__(self, unique_id, model, max_power, name, blockchain_id=None):
        super().__init__(unique_id, model)
        self.max_power = max_power
        self.consumed_power = 0
        
        self.total_cost = 0
        self.energy_supplied = 0
        
        self.name = name
        self.blockchain_id = blockchain_id  # ID de l'agent sur la blockchain
        self.interactions = {}

    def interact(self, other_agent):
        self.interactions[other_agent.name] += 1
        other_agent.interactions[self.name] += 1

    def consume_power(self, power):
        # Vérifie limite de puissance souscrite
        if self.consumed_power + power > self.max_power:
            raise ValueError("Grid power exceeds subscribed limit.")
        
        cost_grid_current = self.model.C_grid[self.model.schedule.steps]
        self.consumed_power += power
        self.total_cost += power * cost_grid_current
        self.energy_supplied += power

    def step(self):
        # Remise à zéro de la puissance consommée chaque heure
        self.consumed_power = 0

    def finalize(self):
        pass


# =========================================================
# Définition du Modèle
# =========================================================
class EnergyManagementModel(Model):
    def __init__(
        self, 
        data, 
        preferences,
        soc_ev, 
        soc_storage, 
        soc_min_storage, 
        soc_max_storage,
        blockchain_bridge=None,
        contract_address=None
    ):
        super().__init__()
        self.schedule = BaseScheduler(self)
        
        # On suppose 24 pas de temps (24 heures)
        self.delta_t = 1
        
        # =====================================================
        # Stockage des tableaux de coûts dans le modèle
        # =====================================================
        self.C_grid = C_grid_array
        self.C_pv = C_pv_array
        self.C_storage = C_storage_array
        
        # =====================================================
        # Initialisation de la connexion blockchain
        # =====================================================
        self.blockchain_bridge = blockchain_bridge
        
        # Initialisation des métriques blockchain
        self.blockchain_metrics = BlockchainMetrics(blockchain_bridge) if blockchain_bridge else None
        
        # Matrice pour stocker les coûts horaires par agent
        self.hourly_costs = pd.DataFrame()
        
        if blockchain_bridge is not None and contract_address is not None:
            try:
                self.blockchain_bridge.connect_to_contract(contract_address)
                print(f"Connecté au contrat blockchain: {contract_address}")
                
                # Récupérer le nombre d'agents existants sur la blockchain
                self.blockchain_agent_count = self.blockchain_bridge.get_agent_count()
                print(f"Nombre d'agents sur la blockchain: {self.blockchain_agent_count}")
                
                # Initialiser les métriques de taille de blockchain
                if self.blockchain_metrics:
                    self.blockchain_metrics.update_blockchain_size()
            except Exception as e:
                print(f"Erreur lors de la connexion au contrat blockchain: {e}")
                self.blockchain_bridge = None
                self.blockchain_metrics = None

        # =====================================================
        # Initialisation des agents
        # =====================================================
        blockchain_agent_index = 0  # Index pour suivre les IDs blockchain
        
        # 1) Agent PV
        self.pv_agent = PVAgent(
            unique_id=0,
            model=self,
            power_profile=data['PV_total'].to_numpy(),
            name="PV",
            blockchain_id=blockchain_agent_index if self.blockchain_bridge is not None else None
        )
        self.schedule.add(self.pv_agent)
        
        # Enregistrer l'agent PV sur la blockchain si la connexion est établie
        if self.blockchain_bridge is not None:
            try:
                # Convertir le profil de puissance en format blockchain (Wei)
                power_profile = [int(p * 10**18) for p in data['PV_total'].to_numpy()]
                
                # Enregistrer l'agent sur la blockchain avec mesure de performance
                if self.blockchain_metrics:
                    def register_pv_agent_call():
                        return self.blockchain_bridge.contract.functions.registerPVAgent(
                            "PV",
                            self.blockchain_bridge.web3.eth.accounts[9],  # Utiliser le compte 9 pour PV (comme dans deploy.js)
                            power_profile
                        ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                    
                    receipt = self.blockchain_metrics.measure_transaction('register_agent', register_pv_agent_call)
                    if receipt:
                        print(f"Agent PV enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                else:
                    # Version originale sans métriques
                    receipt = self.blockchain_bridge.contract.functions.registerPVAgent(
                        "PV",
                        self.blockchain_bridge.web3.eth.accounts[9],
                        power_profile
                    ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                    print(f"Agent PV enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                
                blockchain_agent_index += 1
            except Exception as e:
                print(f"Erreur lors de l'enregistrement de l'agent PV sur la blockchain: {e}")
                if self.blockchain_metrics:
                    self.blockchain_metrics.transaction_success['register_agent']['failed'] += 1

        # 2) Agent Stockage
        self.storage_agent = StorageAgent(
            unique_id=1,
            model=self,
            soc=soc_storage,
            max_soc=soc_max_storage,
            min_soc=soc_min_storage,
            charge_power=40,         # kW
            discharge_power=80,      # kW
            efficiency=0.98,
            name="Storage",
            blockchain_id=blockchain_agent_index if self.blockchain_bridge is not None else None
        )
        self.schedule.add(self.storage_agent)
        
        # Enregistrer l'agent Stockage sur la blockchain
        if self.blockchain_bridge is not None:
            try:
                if self.blockchain_metrics:
                    def register_storage_agent_call():
                        return self.blockchain_bridge.contract.functions.registerStorageAgent(
                            "Storage",
                            self.blockchain_bridge.web3.eth.accounts[9],  # Compte 9 pour Storage
                            80,  # alpha
                            20,  # beta
                            0,   # gamma
                            int(soc_storage * 100),  # soc (convertir en pourcentage)
                            int(soc_max_storage * 100),  # socMax
                            int(soc_min_storage * 100),  # socMin
                            40000,  # chargePower (40kW)
                            80000,  # dischargePower (80kW)
                            98     # efficiency (98%)
                        ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                    
                    receipt = self.blockchain_metrics.measure_transaction('register_agent', register_storage_agent_call)
                    if receipt:
                        print(f"Agent Stockage enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                else:
                    receipt = self.blockchain_bridge.contract.functions.registerStorageAgent(
                        "Storage",
                        self.blockchain_bridge.web3.eth.accounts[9],  # Compte 9 pour Storage
                        80,  # alpha
                        20,  # beta
                        0,   # gamma
                        int(soc_storage * 100),  # soc (convertir en pourcentage)
                        int(soc_max_storage * 100),  # socMax
                        int(soc_min_storage * 100),  # socMin
                        40000,  # chargePower (40kW)
                        80000,  # dischargePower (80kW)
                        98     # efficiency (98%)
                    ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                    print(f"Agent Stockage enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                
                blockchain_agent_index += 1
            except Exception as e:
                print(f"Erreur lors de l'enregistrement de l'agent Stockage: {e}")
                if self.blockchain_metrics:
                    self.blockchain_metrics.transaction_success['register_agent']['failed'] += 1

        # 3) Agent Réseau
        self.grid_agent = GridAgent(
            unique_id=2,
            model=self,
            max_power=580,
            name="Grid",
            blockchain_id=blockchain_agent_index if self.blockchain_bridge is not None else None
        )
        self.schedule.add(self.grid_agent)
        
        # Enregistrer l'agent Réseau sur la blockchain
        if self.blockchain_bridge is not None:
            try:
                if self.blockchain_metrics:
                    def register_grid_agent_call():
                        return self.blockchain_bridge.contract.functions.registerGridAgent(
                            "Grid",
                            self.blockchain_bridge.web3.eth.accounts[9]  # Compte 9 pour Grid
                        ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                    
                    receipt = self.blockchain_metrics.measure_transaction('register_agent', register_grid_agent_call)
                    if receipt:
                        print(f"Agent Réseau enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                else:
                    receipt = self.blockchain_bridge.contract.functions.registerGridAgent(
                        "Grid",
                        self.blockchain_bridge.web3.eth.accounts[9]  # Compte 9 pour Grid
                    ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                    print(f"Agent Réseau enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                
                blockchain_agent_index += 1
            except Exception as e:
                print(f"Erreur lors de l'enregistrement de l'agent Réseau: {e}")
                if self.blockchain_metrics:
                    self.blockchain_metrics.transaction_success['register_agent']['failed'] += 1

        # 4) Agents Bâtiments
        self.building_agents = []
        for i in range(4):
            building_agent = BuildingAgent(
                unique_id=i + 3,
                model=self,
                demand_profile=data.iloc[:, i + 1].to_numpy(),
                preferences=preferences['building'][i],
                name=f"Building {i + 1}",
                blockchain_id=blockchain_agent_index if self.blockchain_bridge is not None else None
            )
            self.schedule.add(building_agent)
            self.building_agents.append(building_agent)
            
            # Enregistrer l'agent Bâtiment sur la blockchain
            if self.blockchain_bridge is not None:
                try:
                    # Convertir le profil de demande en format blockchain (Wei)
                    demand_profile = [int(d * 10**18) for d in data.iloc[:, i + 1].to_numpy()]
                    
                    if self.blockchain_metrics:
                        def register_building_agent_call():
                            return self.blockchain_bridge.contract.functions.registerBuildingAgent(
                                f"Building {i + 1}",
                                self.blockchain_bridge.web3.eth.accounts[i + 1],  # Comptes 1-4 pour Buildings
                                80,  # alpha (convertir de 0.8 à 80)
                                10,  # beta (convertir de 0.1 à 10)
                                10,  # gamma (convertir de 0.1 à 10)
                                demand_profile
                            ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                        
                        receipt = self.blockchain_metrics.measure_transaction('register_agent', register_building_agent_call)
                        if receipt:
                            print(f"Agent Bâtiment {i+1} enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                    else:
                        receipt = self.blockchain_bridge.contract.functions.registerBuildingAgent(
                            f"Building {i + 1}",
                            self.blockchain_bridge.web3.eth.accounts[i + 1],  # Comptes 1-4 pour Buildings
                            80,  # alpha (convertir de 0.8 à 80)
                            10,  # beta (convertir de 0.1 à 10)
                            10,  # gamma (convertir de 0.1 à 10)
                            demand_profile
                        ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                        print(f"Agent Bâtiment {i+1} enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                    
                    blockchain_agent_index += 1
                except Exception as e:
                    print(f"Erreur lors de l'enregistrement de l'agent Bâtiment {i+1}: {e}")
                    if self.blockchain_metrics:
                        self.blockchain_metrics.transaction_success['register_agent']['failed'] += 1

        # 5) Agents Véhicules Électriques (EV)
        # Exemple de caractéristiques et créneaux d'arrivée/départ
        self.ev_agents = []
        ev_characteristics = [
            {'soc': 0.2, 'soc_required': 0.6, 'max_power': 22, 'eta': 0.8, 'arrival': 9, 'departure': 12, 'name': 'EV 1'},
            {'soc': 0.45, 'soc_required': 0.8, 'max_power': 22, 'eta': 0.8, 'arrival': 10, 'departure': 19, 'name': 'EV 2'},
            {'soc': 0.4, 'soc_required': 0.8, 'max_power': 7.2, 'eta': 0.8, 'arrival': 11, 'departure': 16, 'name': 'EV 3'},
            {'soc': 0.25, 'soc_required': 0.85, 'max_power': 22, 'eta': 0.8, 'arrival': 10, 'departure': 18, 'name': 'EV 4'},
        ]
        
        for i, ev in enumerate(ev_characteristics):
            ev_agent = EVAgent(
                unique_id=i + 7,
                model=self,
                soc=ev['soc'],
                soc_required=ev['soc_required'],
                max_power=ev['max_power'],
                eta=ev['eta'],
                preferences=preferences['EV'][i],
                arrival=ev['arrival'],
                departure=ev['departure'],
                name=ev['name'],
                blockchain_id=blockchain_agent_index if self.blockchain_bridge is not None else None
            )
            self.schedule.add(ev_agent)
            self.ev_agents.append(ev_agent)
            
            # Enregistrer l'agent EV sur la blockchain
            if self.blockchain_bridge is not None:
                try:
                    if self.blockchain_metrics:
                        def register_ev_agent_call():
                            return self.blockchain_bridge.contract.functions.registerEVAgent(
                                ev['name'],
                                self.blockchain_bridge.web3.eth.accounts[i + 5],  # Comptes 5-8 pour EVs
                                80,  # alpha (convertir de 0.8 à 80)
                                10,  # beta (convertir de 0.1 à 10)
                                10,  # gamma (convertir de 0.1 à 10)
                                int(ev['soc'] * 100),  # soc (convertir en pourcentage)
                                int(ev['soc_required'] * 100),  # socRequired (convertir en pourcentage)
                                int(ev['max_power'] * 1000),  # maxPower (convertir en W)
                                int(ev['eta'] * 100),  # efficiency (convertir en pourcentage)
                                int(ev['arrival']),  # arrivalHour
                                int(ev['departure'])   # departureHour
                            ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                        
                        receipt = self.blockchain_metrics.measure_transaction('register_agent', register_ev_agent_call)
                        if receipt:
                            print(f"Agent EV {i+1} enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                    else:
                        receipt = self.blockchain_bridge.contract.functions.registerEVAgent(
                            ev['name'],
                            self.blockchain_bridge.web3.eth.accounts[i + 5],  # Comptes 5-8 pour EVs
                            80,  # alpha (convertir de 0.8 à 80)
                            10,  # beta (convertir de 0.1 à 10)
                            10,  # gamma (convertir de 0.1 à 10)
                            int(ev['soc'] * 100),  # soc (convertir en pourcentage)
                            int(ev['soc_required'] * 100),  # socRequired (convertir en pourcentage)
                            int(ev['max_power'] * 1000),  # maxPower (convertir en W)
                            int(ev['eta'] * 100),  # efficiency (convertir en pourcentage)
                            int(ev['arrival']),  # arrivalHour
                            int(ev['departure'])   # departureHour
                        ).transact({'from': self.blockchain_bridge.web3.eth.accounts[0], 'gas': 5000000})
                        print(f"Agent EV {i+1} enregistré sur la blockchain: {receipt['transactionHash'].hex()}")
                    
                    blockchain_agent_index += 1
                except Exception as e:
                    print(f"Erreur lors de l'enregistrement de l'agent EV {i+1}: {e}")
                    if self.blockchain_metrics:
                        self.blockchain_metrics.transaction_success['register_agent']['failed'] += 1

        # Création d'un dictionnaire d'interactions pour chaque agent
        for agent in self.schedule.agents:
            agent.interactions = {
                other_agent.name: 0 for other_agent in self.schedule.agents
            }
            
        # Création de la matrice d'interactions entre agents
        self.interaction_matrix = np.zeros((len(self.schedule.agents), len(self.schedule.agents)))
        
        # Stockage des coûts horaires
        self.hourly_costs = pd.DataFrame(
            index=range(24),
            columns=[agent.name for agent in self.schedule.agents if hasattr(agent, 'total_cost')]
        )

        # DataCollector pour suivre les interactions
        self.datacollector = DataCollector(
            model_reporters={
                "Total Interactions": self.get_total_interactions,
            },
            agent_reporters={
                "Interactions": lambda agent: sum(agent.interactions.values())
            }
        )

    def get_total_interactions(self):
        return sum(sum(agent.interactions.values()) for agent in self.schedule.agents)

    def step(self):
        current_hour = self.schedule.steps
        
        self.datacollector.collect(self)
        self.schedule.step()
        
        # Collecter les coûts horaires
        for agent in self.schedule.agents:
            if hasattr(agent, 'total_cost') and agent.name in self.hourly_costs.columns:
                cost_this_hour = 0
                if hasattr(agent, 'cost_pv'):
                    cost_this_hour += agent.cost_pv
                if hasattr(agent, 'cost_storage'):
                    cost_this_hour += agent.cost_storage
                if hasattr(agent, 'cost_grid'):
                    cost_this_hour += agent.cost_grid
                
                self.hourly_costs.loc[current_hour, agent.name] = cost_this_hour
        
        # Mettre à jour la matrice d'interactions
        for i, agent1 in enumerate(self.schedule.agents):
            for j, agent2 in enumerate(self.schedule.agents):
                if hasattr(agent1, 'interactions') and agent2.name in agent1.interactions:
                    self.interaction_matrix[i, j] = agent1.interactions[agent2.name]
        
        # Avancer l'heure sur la blockchain si la connexion est établie
        if self.blockchain_bridge is not None:
            try:
                # Mise à jour des métriques blockchain avant la transaction
                if self.blockchain_metrics:
                    self.blockchain_metrics.update_blockchain_size()
                
                # Avancer l'heure du contrat avec mesure de performance
                if self.blockchain_metrics:
                    def advance_hour_call():
                        return self.blockchain_bridge.contract.functions.advanceHour().transact({
                            'from': self.blockchain_bridge.web3.eth.accounts[0], 
                            'gas': 500000
                        })
                    
                    receipt = self.blockchain_metrics.measure_transaction('advance_hour', advance_hour_call)
                    if receipt:
                        print(f"Heure avancée sur la blockchain: {current_hour}")
                else:
                    # Code original sans métriques
                    self.blockchain_bridge.contract.functions.advanceHour().transact({
                        'from': self.blockchain_bridge.web3.eth.accounts[0], 
                        'gas': 500000
                    })
                    print(f"Heure avancée sur la blockchain: {current_hour}")
        
                
                # Collecter les événements blockchain
                if self.blockchain_metrics:
                    self.blockchain_metrics.collect_events()
                
            except Exception as e:
                print(f"Erreur lors de l'avancement de l'heure sur la blockchain: {e}")
                if self.blockchain_metrics:
                    self.blockchain_metrics.transaction_success['advance_hour']['failed'] += 1
    
    def generate_blockchain_metrics_report(self, output_dir='blockchain_metrics'):
        """
        Génère un rapport complet des métriques blockchain
        """
        if not self.blockchain_metrics:
            print("Pas de métriques blockchain disponibles")
            return
        
        # Créer le répertoire de sortie si nécessaire
        os.makedirs(output_dir, exist_ok=True)
        
        # Mettre à jour les données des agents
        self.blockchain_metrics.set_agent_data(self.schedule.agents, self.interaction_matrix)
        
        # Si nous avons des coûts horaires, les ajouter aux métriques
        if not self.hourly_costs.empty:
            self.blockchain_metrics.hourly_costs = self.hourly_costs
        
        # Générer le rapport
        report = self.blockchain_metrics.generate_report()
        
        # Sauvegarder le rapport au format JSON
        with open(f"{output_dir}/blockchain_metrics_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Générer les visualisations
        self.blockchain_metrics.visualize_metrics(output_dir)
        
        # Afficher un résumé du rapport
        print("\n===== BLOCKCHAIN METRICS REPORT =====")
        print(f"Coefficient de Gini (distribution des coûts): {report['gini_coefficient']:.4f}")
        print(f"Transactions par seconde moyen: {report['tps']:.4f} TPS")
        
        # Statistiques des transactions
        print("\nPerformance des transactions:")
        for tx_type, stats in report['transaction_stats'].items():
            if stats['avg_time'] > 0:  # Ne montrer que les types de transactions utilisés
                print(f"  {tx_type}: {stats['avg_time']:.4f}s, {stats['avg_gas']:.0f} gaz, {stats['success_rate']*100:.1f}% succès")
        
        # Distribution des événements
        print("\nDistribution des événements:")
        for event_type, count in report['event_distribution'].items():
            if count > 0:
                print(f"  {event_type}: {count}")
        
        # Taille de la blockchain
        print(f"\nTaille approximative de la blockchain: {report['blockchain_size'] / 1024:.2f} KB")
        
        print("\nLes visualisations ont été sauvegardées dans le dossier:", output_dir)
        print("=============================================\n")
        
        return report


# =========================================================
# Fonction d'exécution principale avec blockchain
# =========================================================
def run_energy_management_with_blockchain(contract_address=None):
    """
    Exécuter le modèle avec intégration blockchain
    
    Args:
        contract_address: L'adresse du contrat déployé sur la blockchain Ganache
    """
    print("Initialisation du modèle de gestion d'énergie avec intégration blockchain...")
    
    # Conditions initiales pour la batterie stationnaire et les VE
    SOC_EV = np.array([0.2, 0.45, 0.4, 0.25])
    SOC_storage = 0.35
    SOC_min_storage = 0.1
    SOC_max_storage = 1.0
    
    # Initialiser la connexion blockchain
    blockchain_bridge = None
    if contract_address:
        try:
            blockchain_bridge = BlockchainBridge()
            print("Connexion blockchain initialisée")
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la connexion blockchain: {e}")
            blockchain_bridge = None
    
    # Initialiser le modèle
    model = EnergyManagementModel(
        data=data,
        preferences=preferences,
        soc_ev=SOC_EV,
        soc_storage=SOC_storage,
        soc_min_storage=SOC_min_storage,
        soc_max_storage=SOC_max_storage,
        blockchain_bridge=blockchain_bridge,
        contract_address=contract_address
    )
    
    # Boucle sur 24 heures
    for i in range(24):
        print(f"====== Hour {i} ======")
        model.step()
        # Petite pause pour éviter de saturer la blockchain
        if blockchain_bridge is not None:
            time.sleep(1)  
    
    # Finalisation et collecte des données
    for agent in model.schedule.agents:
        if isinstance(agent, (BuildingAgent, EVAgent, StorageAgent, PVAgent)):
            agent.finalize()
    
    # Récupération des résultats dans un DataFrame
    results = []
    for agent in model.schedule.agents:
        if isinstance(agent, BuildingAgent):
            results.append({
                'User Name': agent.preferences['name'],
                'Cost ($)': -agent.total_cost,  # On met le coût en négatif pour rester cohérent avec le signe
                'Comfort': agent.comfort,
                'PV Used (kWh)': agent.pv_used
            })
        elif isinstance(agent, EVAgent):
            results.append({
                'User Name': agent.preferences['name'],
                'Cost ($)': -agent.total_cost,
                'Comfort': agent.comfort,
                'PV Used (kWh)': agent.pv_used
            })
        elif isinstance(agent, StorageAgent):
            results.append({
                'User Name': 'Storage',
                'Cost ($)': agent.total_cost,
                'Comfort': agent.comfort,
                'PV Used (kWh)': agent.pv_used
            })
        elif isinstance(agent, PVAgent):
            results.append({
                'User Name': 'PV',
                'Cost ($)': agent.revenue,  # Revenue PV
                'Comfort': None,
                'PV Used (kWh)': agent.energy_sold
            })
    
    results_df = pd.DataFrame(results)
    average_comfort = results_df['Comfort'].dropna().mean()
    
    print("\n===== RESULTS =====")
    print(results_df)
    print(f"Average Comfort: {average_comfort:.2f}")
    total_cost = results_df['Cost ($)'].sum()
    print(f"Total Cost: {total_cost:.2f}")
    
    # Comparaison avec les coûts blockchain si disponible
    if blockchain_bridge is not None:
        print("\n===== BLOCKCHAIN COSTS =====")
        try:
            # Ne vérifier que le nombre d'agents effectivement enregistrés
            actual_agent_count = min(model.blockchain_agent_count, 11)  # Maximum de 11 agents (PV, Storage, Grid, 4 Buildings, 4 EVs)
            for i in range(actual_agent_count):
                cost = blockchain_bridge.contract.functions.calculateTotalCost(i).call()
                cost_eth = blockchain_bridge.web3.from_wei(cost, 'ether')
                agent_type = "Unknown"
                if i < 3:
                    agent_type = ["PV", "Storage", "Grid"][i]
                elif i < 7:
                    agent_type = f"Building {i-2}"
                elif i < 11:
                    agent_type = f"EV {i-6}"
                
                print(f"{agent_type} blockchain cost: {cost_eth} ETH")
        except Exception as e:
            print(f"Erreur lors de la récupération des coûts blockchain: {e}")
        
    # Générer le rapport des métriques blockchain
    if model.blockchain_metrics is not None:
        model.generate_blockchain_metrics_report()
    
    return model, results_df


# =========================================================
# Si le script est exécuté directement
# =========================================================
import sys

if __name__ == "__main__":
    
    # Vérifier si une adresse de contrat est fournie en argument
    contract_address = None
    if len(sys.argv) > 1:
        contract_address = sys.argv[1]
    else:
        # Demander l'adresse du contrat à l'utilisateur
        contract_address = input("Entrez l'adresse du contrat déployé (laisser vide pour exécuter sans blockchain): ")
        if not contract_address:
            contract_address = None
    
    # Exécuter le modèle
    model, results = run_energy_management_with_blockchain(contract_address)
    
    # Affichage des graphiques (si souhaité)
    # Exemple de tracé : évolutions des interactions
    model_data = model.datacollector.get_model_vars_dataframe()
    
    plt.figure(figsize=(10, 6))
    plt.plot(model_data.index, model_data['Total Interactions'], label='Total Interactions')
    plt.xlabel('Time Step')
    plt.ylabel('Total Interactions')
    plt.title('Total Interactions Over Time')
    plt.legend()
    plt.grid(True)
    plt.show()