import json
import os
from web3 import Web3

class BlockchainBridge:
    """
    Pont entre le système multi-agents Python et la blockchain Ethereum (Ganache)
    """
    def __init__(self, ganache_url="http://127.0.0.1:7545"):
        """
        Initialise la connexion à la blockchain

        Args:
            ganache_url (str): URL de l'instance Ganache
        """
        self.web3 = Web3(Web3.HTTPProvider(ganache_url))
        
        if not self.web3.is_connected():
            raise Exception(f"Impossible de se connecter à la blockchain à l'adresse {ganache_url}")
        
        print(f"Connecté à la blockchain avec succès")
        print(f"Block actuel: {self.web3.eth.block_number}")
        
        self.contract = None
        self.contract_address = None
        self.contract_abi = None
    
    def connect_to_contract(self, contract_address):
        """
        Se connecte à un contrat intelligent existant

        Args:
            contract_address (str): Adresse du contrat déployé
        """
        # Charger l'ABI du contrat
        try:
            # Chemin relatif vers le fichier ABI
            abi_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                '../build/contracts/EnergyManagementSystem.json'
            )
            
            with open(abi_path, 'r') as f:
                contract_data = json.load(f)
                self.contract_abi = contract_data['abi']
        except Exception as e:
            # Fallback: utiliser un ABI minimal pour les fonctions principales
            print(f"Erreur lors du chargement de l'ABI: {e}")
            print("Utilisation d'un ABI minimal")
            
            self.contract_abi = [
                {
                    "inputs": [],
                    "name": "getAgentCount",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "advanceHour",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "availablePV", "type": "uint256"}, {"name": "availableStorage", "type": "uint256"}],
                    "name": "updateEnergySources",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "buildingId", "type": "uint256"}],
                    "name": "allocateBuildingEnergy",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "evId", "type": "uint256"}],
                    "name": "allocateEVEnergy",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "agentId", "type": "uint256"}],
                    "name": "calculateTotalCost",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "fromAgentId", "type": "uint256"}, {"name": "toAgentId", "type": "uint256"}, {"name": "amount", "type": "uint256"}],
                    "name": "processPayment",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "name", "type": "string"}, {"name": "agentOwner", "type": "address"}, {"name": "powerProfile", "type": "uint256[]"}],
                    "name": "registerPVAgent",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "name", "type": "string"}, {"name": "agentOwner", "type": "address"}, {"name": "alpha", "type": "uint8"}, {"name": "beta", "type": "uint8"}, {"name": "gamma", "type": "uint8"}, {"name": "soc", "type": "uint8"}, {"name": "socMax", "type": "uint8"}, {"name": "socMin", "type": "uint8"}, {"name": "chargePower", "type": "uint256"}, {"name": "dischargePower", "type": "uint256"}, {"name": "efficiency", "type": "uint8"}],
                    "name": "registerStorageAgent",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "name", "type": "string"}, {"name": "agentOwner", "type": "address"}],
                    "name": "registerGridAgent",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "name", "type": "string"}, {"name": "agentOwner", "type": "address"}, {"name": "alpha", "type": "uint8"}, {"name": "beta", "type": "uint8"}, {"name": "gamma", "type": "uint8"}, {"name": "demandProfile", "type": "uint256[]"}],
                    "name": "registerBuildingAgent",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "name", "type": "string"}, {"name": "agentOwner", "type": "address"}, {"name": "alpha", "type": "uint8"}, {"name": "beta", "type": "uint8"}, {"name": "gamma", "type": "uint8"}, {"name": "soc", "type": "uint8"}, {"name": "socRequired", "type": "uint8"}, {"name": "maxPower", "type": "uint256"}, {"name": "efficiency", "type": "uint8"}, {"name": "arrivalHour", "type": "uint8"}, {"name": "departureHour", "type": "uint8"}],
                    "name": "registerEVAgent",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
        
        # Valider l'adresse du contrat
        if not self.web3.is_address(contract_address):
            raise ValueError(f"Adresse de contrat invalide: {contract_address}")
        
        self.contract_address = self.web3.to_checksum_address(contract_address)
        
        # Créer l'instance du contrat
        self.contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )
        
        print(f"Connecté au contrat à l'adresse {self.contract_address}")
    
    def get_agent_count(self):
        """
        Récupère le nombre d'agents enregistrés sur la blockchain
        
        Returns:
            int: Nombre d'agents
        """
        if not self.contract:
            raise Exception("Pas de contrat connecté")
        
        return self.contract.functions.getAgentCount().call()
    
    def process_payment(self, agent_id, account_index):
        """
        Traite le paiement pour un agent
        
        Args:
            agent_id (int): ID de l'agent
            account_index (int): Index du compte Ganache à utiliser
            
        Returns:
            receipt: Reçu de transaction
        """
        if not self.contract:
            raise Exception("Pas de contrat connecté")
        
        # Récupérer le coût total
        cost = self.contract.functions.calculateTotalCost(agent_id).call()
        
        # Compte à utiliser pour le paiement
        account = self.web3.eth.accounts[account_index]
        
        # Trouver l'agent PV pour le paiement (généralement l'agent 0)
        pv_agent_id = 0
        
        # Effectuer le paiement
        tx_hash = self.contract.functions.processPayment(
            agent_id, pv_agent_id, cost
        ).transact({
            'from': account, 
            'value': cost,  # Pour un contrat payable
            'gas': 1000000
        })
        
        # Attendre la confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt


if __name__ == "__main__":
    # Test de connexion
    try:
        bridge = BlockchainBridge()
        print("Connexion à la blockchain réussie!")
    except Exception as e:
        print(f"Erreur de connexion: {e}")
