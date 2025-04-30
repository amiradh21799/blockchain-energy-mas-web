// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title EnergyManagementSystem
 * @dev Contrat principal pour la gestion décentralisée de l'énergie
 */
contract EnergyManagementSystem {
    address public owner;
    uint256 public currentHour;
    
    // Types d'agents
    enum AgentType { PV, Storage, Grid, Building, EV }
    
    // Structure pour les agents
    struct Agent {
        uint256 id;
        string name;
        address owner;
        AgentType agentType;
        bool active;
    }

    // Structure pour les données de prix
    struct PriceData {
        uint256 pvPrice;      // Prix du PV par kWh (multiplié par 100)
        uint256 gridPrice;    // Prix du réseau par kWh (multiplié par 100)
        uint256 storagePrice; // Prix du stockage par kWh (multiplié par 100)
    }

    // Structure pour les préférences des agents
    struct Preferences {
        uint8 alpha;  // Préférence pour le réseau (en pourcentage)
        uint8 beta;   // Préférence pour le PV (en pourcentage)
        uint8 gamma;  // Préférence pour le stockage (en pourcentage)
    }

    // Structure pour les agents PV
    struct PVData {
        uint256[] powerProfile; // Profil de puissance du PV pour 24 heures
        uint256 availablePower; // Puissance disponible à l'heure actuelle
        uint256 energySold;     // Énergie vendue
        uint256 revenue;        // Revenus générés
    }

    // Structure pour les agents de stockage
    struct StorageData {
        uint8 soc;                  // État de charge actuel (pourcentage)
        uint8 socMax;               // État de charge maximum (pourcentage)
        uint8 socMin;               // État de charge minimum (pourcentage)
        uint256 chargePower;        // Puissance de charge (W)
        uint256 dischargePower;     // Puissance de décharge (W)
        uint8 efficiency;           // Efficacité (pourcentage)
        uint256 availableDischargePower; // Puissance de décharge disponible
    }

    // Structure pour les agents bâtiments
    struct BuildingData {
        uint256[] demandProfile;    // Profil de demande pour 24 heures
        uint256 consumedFromPV;      // Énergie consommée du PV
        uint256 consumedFromStorage; // Énergie consommée du stockage
        uint256 consumedFromGrid;    // Énergie consommée du réseau
    }

    // Structure pour les agents EV
    struct EVData {
        uint8 soc;             // État de charge actuel (pourcentage)
        uint8 socRequired;     // État de charge requis (pourcentage)
        uint256 maxPower;      // Puissance maximale (W)
        uint8 efficiency;      // Efficacité (pourcentage)
        uint8 arrivalHour;     // Heure d'arrivée
        uint8 departureHour;   // Heure de départ
        uint256 consumedFromPV;      // Énergie consommée du PV
        uint256 consumedFromStorage; // Énergie consommée du stockage
        uint256 consumedFromGrid;    // Énergie consommée du réseau
    }

    // Structure pour le réseau
    struct GridData {
        uint256 maxPower;     // Puissance maximale disponible
        uint256 consumedPower; // Puissance consommée
        uint256 energySupplied; // Énergie fournie
    }

    // Structures pour suivre les coûts des agents
    struct AgentCosts {
        uint256 pvCost;      // Coût du PV
        uint256 storageCost; // Coût du stockage
        uint256 gridCost;    // Coût du réseau
        uint256 totalCost;   // Coût total
    }

    // Cartographie des données
    mapping(uint256 => Agent) public agents;
    mapping(uint256 => Preferences) public agentPreferences;
    mapping(uint256 => PVData) public pvAgents;
    mapping(uint256 => StorageData) public storageAgents;
    mapping(uint256 => BuildingData) public buildingAgents;
    mapping(uint256 => EVData) public evAgents;
    mapping(uint256 => GridData) public gridAgents;
    mapping(uint256 => AgentCosts) public agentCosts;
    mapping(uint256 => PriceData) public hourlyPrices;

    uint256 public agentCount = 0;
    uint256 public pvAgentCount = 0;
    uint256 public storageAgentCount = 0;
    uint256 public gridAgentCount = 0;
    uint256 public buildingAgentCount = 0;
    uint256 public evAgentCount = 0;

    // Variables pour l'allocation d'énergie
    uint256 public totalAvailablePVPower = 0;
    uint256 public totalAvailableStoragePower = 0;

    // Événements
    event AgentRegistered(uint256 indexed agentId, string name, AgentType agentType);
    event EnergyAllocated(uint256 indexed consumerId, uint256 indexed providerId, uint256 amount, uint256 price);
    event HourAdvanced(uint256 newHour);
    event PriceUpdated(uint256 hour, uint256 pvPrice, uint256 gridPrice, uint256 storagePrice);
    event EnergyCostCalculated(uint256 indexed agentId, uint256 totalCost);
    event PaymentProcessed(uint256 indexed fromAgent, uint256 indexed toAgent, uint256 amount);
    event ResourcesUpdated(uint256 availablePV, uint256 availableStorage);

    /**
     * @dev Constructeur - initialise les prix de l'énergie pour les 24 heures
     */
    constructor() {
        owner = msg.sender;
        currentHour = 0;
        
        // Initialiser les prix pour chaque heure (exemple)
        for(uint256 i = 0; i < 24; i++) {
            PriceData memory prices;
            
            // Prix PV: 0.10 $/kWh
            prices.pvPrice = 10;
            
            // Prix réseau: heures creuses (0.05 $/kWh) / heures pleines (0.12 $/kWh)
            if(i < 6 || i >= 22) {
                prices.gridPrice = 5; // Heures creuses
            } else {
                prices.gridPrice = 12; // Heures pleines
            }
            
            // Prix stockage: heures creuses (0.35 $/kWh) / heures pleines (0.40 $/kWh)
            if(i < 6 || i >= 22) {
                prices.storagePrice = 35; // Heures creuses
            } else {
                prices.storagePrice = 40; // Heures pleines
            }
            
            hourlyPrices[i] = prices;
        }
    }

    /**
     * @dev Modifier - Vérifie que l'appelant est le propriétaire
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "Seul le proprietaire peut appeler cette fonction");
        _;
    }

    /**
     * @dev Avance l'heure courante (cycle des 24h)
     */
    function advanceHour() public onlyOwner {
        currentHour = (currentHour + 1) % 24;
        emit HourAdvanced(currentHour);
    }

    /**
     * @dev Met à jour les prix de l'énergie pour une heure spécifique
     */
    function updatePrices(uint256 hour, uint256 pvPrice, uint256 gridPrice, uint256 storagePrice) public onlyOwner {
        require(hour < 24, "Heure invalide");
        
        hourlyPrices[hour].pvPrice = pvPrice;
        hourlyPrices[hour].gridPrice = gridPrice;
        hourlyPrices[hour].storagePrice = storagePrice;
        
        emit PriceUpdated(hour, pvPrice, gridPrice, storagePrice);
    }

    /**
     * @dev Enregistre un nouvel agent PV
     */
    function registerPVAgent(string memory name, address agentOwner, uint256[] memory powerProfile) public onlyOwner returns (uint256) {
        uint256 agentId = agentCount;
        
        agents[agentId] = Agent(agentId, name, agentOwner, AgentType.PV, true);
        
        // Préférences par défaut pour PV
        agentPreferences[agentId] = Preferences(80, 10, 10);
        
        // Données spécifiques PV
        pvAgents[agentId] = PVData(powerProfile, 0, 0, 0);
        
        // Coûts initiaux
        agentCosts[agentId] = AgentCosts(0, 0, 0, 0);
        
        agentCount++;
        pvAgentCount++;
        
        emit AgentRegistered(agentId, name, AgentType.PV);
        return agentId;
    }

    /**
     * @dev Enregistre un nouvel agent de stockage
     */
    function registerStorageAgent(
        string memory name, 
        address agentOwner,
        uint8 alpha,
        uint8 beta,
        uint8 gamma,
        uint8 soc,
        uint8 socMax,
        uint8 socMin,
        uint256 chargePower,
        uint256 dischargePower,
        uint8 efficiency
    ) public onlyOwner returns (uint256) {
        uint256 agentId = agentCount;
        
        agents[agentId] = Agent(agentId, name, agentOwner, AgentType.Storage, true);
        
        // Préférences personnalisées
        agentPreferences[agentId] = Preferences(alpha, beta, gamma);
        
        // Données spécifiques stockage
        storageAgents[agentId] = StorageData(soc, socMax, socMin, chargePower, dischargePower, efficiency, 0);
        
        // Coûts initiaux
        agentCosts[agentId] = AgentCosts(0, 0, 0, 0);
        
        // Calcul de la puissance disponible
        uint256 availablePower = calculateAvailableDischargePower(agentId);
        storageAgents[agentId].availableDischargePower = availablePower;
        
        agentCount++;
        storageAgentCount++;
        
        emit AgentRegistered(agentId, name, AgentType.Storage);
        return agentId;
    }

    /**
     * @dev Enregistre un nouvel agent réseau
     */
    function registerGridAgent(string memory name, address agentOwner) public onlyOwner returns (uint256) {
        uint256 agentId = agentCount;
        
        agents[agentId] = Agent(agentId, name, agentOwner, AgentType.Grid, true);
        
        // Préférences par défaut pour Grid
        agentPreferences[agentId] = Preferences(100, 0, 0);
        
        // Données spécifiques réseau - puissance max 580kW
        gridAgents[agentId] = GridData(580 * 1000, 0, 0);
        
        // Coûts initiaux
        agentCosts[agentId] = AgentCosts(0, 0, 0, 0);
        
        agentCount++;
        gridAgentCount++;
        
        emit AgentRegistered(agentId, name, AgentType.Grid);
        return agentId;
    }

    /**
     * @dev Enregistre un nouvel agent bâtiment
     */
    function registerBuildingAgent(
        string memory name, 
        address agentOwner,
        uint8 alpha,
        uint8 beta,
        uint8 gamma,
        uint256[] memory demandProfile
    ) public onlyOwner returns (uint256) {
        uint256 agentId = agentCount;
        
        agents[agentId] = Agent(agentId, name, agentOwner, AgentType.Building, true);
        
        // Préférences personnalisées
        agentPreferences[agentId] = Preferences(alpha, beta, gamma);
        
        // Données spécifiques bâtiment
        buildingAgents[agentId] = BuildingData(demandProfile, 0, 0, 0);
        
        // Coûts initiaux
        agentCosts[agentId] = AgentCosts(0, 0, 0, 0);
        
        agentCount++;
        buildingAgentCount++;
        
        emit AgentRegistered(agentId, name, AgentType.Building);
        return agentId;
    }

    /**
     * @dev Enregistre un nouvel agent EV
     */
    function registerEVAgent(
        string memory name, 
        address agentOwner,
        uint8 alpha,
        uint8 beta,
        uint8 gamma,
        uint8 soc,
        uint8 socRequired,
        uint256 maxPower,
        uint8 efficiency,
        uint8 arrivalHour,
        uint8 departureHour
    ) public onlyOwner returns (uint256) {
        uint256 agentId = agentCount;
        
        agents[agentId] = Agent(agentId, name, agentOwner, AgentType.EV, true);
        
        // Préférences personnalisées
        agentPreferences[agentId] = Preferences(alpha, beta, gamma);
        
        // Données spécifiques EV
        evAgents[agentId] = EVData(soc, socRequired, maxPower, efficiency, arrivalHour, departureHour, 0, 0, 0);
        
        // Coûts initiaux
        agentCosts[agentId] = AgentCosts(0, 0, 0, 0);
        
        agentCount++;
        evAgentCount++;
        
        emit AgentRegistered(agentId, name, AgentType.EV);
        return agentId;
    }

    /**
     * @dev Met à jour les sources d'énergie disponibles (PV et stockage)
     */
    function updateEnergySources(uint256 availablePV, uint256 availableStorage) public {
        totalAvailablePVPower = availablePV;
        totalAvailableStoragePower = availableStorage;
        
        emit ResourcesUpdated(availablePV, availableStorage);
    }

    /**
     * @dev Calcule la puissance de décharge disponible pour un agent de stockage
     */
    function calculateAvailableDischargePower(uint256 storageId) internal view returns (uint256) {
        StorageData storage storageData = storageAgents[storageId];
        
        if (storageData.soc <= storageData.socMin) {
            return 0;
        }
        
        uint256 socDifference = uint256(storageData.soc - storageData.socMin);
        uint256 availablePower = (socDifference * storageData.dischargePower * uint256(storageData.efficiency)) / 100;
        
        return availablePower;
    }

    /**
     * @dev Alloue l'énergie à un bâtiment en fonction de ses préférences
     */
    function allocateBuildingEnergy(uint256 buildingId) public {
        require(agents[buildingId].agentType == AgentType.Building, "L'ID doit correspondre a un batiment");
        
        BuildingData storage building = buildingAgents[buildingId];
        Preferences storage prefs = agentPreferences[buildingId];
        
        // Demande d'énergie pour l'heure actuelle
        uint256 demandWh = building.demandProfile[currentHour];
        
        // Réinitialisation des consommations
        building.consumedFromPV = 0;
        building.consumedFromStorage = 0;
        building.consumedFromGrid = 0;
        
        // Allocation depuis le PV (en fonction de la préférence beta)
        uint256 pvContribution = (totalAvailablePVPower * uint256(prefs.beta)) / 100;
        pvContribution = pvContribution > demandWh ? demandWh : pvContribution;
        
        if (pvContribution > 0) {
            building.consumedFromPV = pvContribution;
            demandWh -= pvContribution;
            totalAvailablePVPower -= pvContribution;
            
            // Enregistrer le coût du PV
            uint256 pvCost = (pvContribution * hourlyPrices[currentHour].pvPrice) / 1000;
            agentCosts[buildingId].pvCost += pvCost;
            agentCosts[buildingId].totalCost += pvCost;
            
            emit EnergyAllocated(buildingId, findPVAgent(), pvContribution, hourlyPrices[currentHour].pvPrice);
        }
        
        // Allocation depuis le stockage (en fonction de la préférence gamma)
        if (demandWh > 0 && totalAvailableStoragePower > 0) {
            uint256 storageContribution = (totalAvailableStoragePower * uint256(prefs.gamma)) / 100;
            storageContribution = storageContribution > demandWh ? demandWh : storageContribution;
            
            if (storageContribution > 0) {
                building.consumedFromStorage = storageContribution;
                demandWh -= storageContribution;
                totalAvailableStoragePower -= storageContribution;
                
                // Enregistrer le coût du stockage
                uint256 storageCost = (storageContribution * hourlyPrices[currentHour].storagePrice) / 1000;
                agentCosts[buildingId].storageCost += storageCost;
                agentCosts[buildingId].totalCost += storageCost;
                
                emit EnergyAllocated(buildingId, findStorageAgent(), storageContribution, hourlyPrices[currentHour].storagePrice);
            }
        }
        
        // Allocation depuis le réseau (en fonction de la préférence alpha)
        if (demandWh > 0) {
            uint256 gridContribution = (demandWh * uint256(prefs.alpha)) / 100;
            
            building.consumedFromGrid = gridContribution;
            
            // Enregistrer le coût du réseau
            uint256 gridCost = (gridContribution * hourlyPrices[currentHour].gridPrice) / 1000;
            agentCosts[buildingId].gridCost += gridCost;
            agentCosts[buildingId].totalCost += gridCost;
            
            emit EnergyAllocated(buildingId, findGridAgent(), gridContribution, hourlyPrices[currentHour].gridPrice);
        }
        
        // Émettre l'événement coût total calculé
        emit EnergyCostCalculated(buildingId, agentCosts[buildingId].totalCost);
    }

    /**
     * @dev Alloue l'énergie à un EV en fonction de ses préférences
     */
    function allocateEVEnergy(uint256 evId) public {
        require(agents[evId].agentType == AgentType.EV, "L'ID doit correspondre a un EV");
        
        EVData storage ev = evAgents[evId];
        Preferences storage prefs = agentPreferences[evId];
        
        // Vérifier si l'EV est présent dans la plage horaire
        if (currentHour < ev.arrivalHour || currentHour >= ev.departureHour || ev.soc >= ev.socRequired) {
            return; // L'EV n'est pas présent ou déjà chargé
        }
        
        // Besoin en énergie pour atteindre la charge requise
        uint256 socDifference = uint256(ev.socRequired - ev.soc);
        uint256 demandWh = (socDifference * ev.maxPower * 100) / uint256(ev.efficiency);
        
        // Réinitialisation des consommations
        ev.consumedFromPV = 0;
        ev.consumedFromStorage = 0;
        ev.consumedFromGrid = 0;
        
        // Allocation depuis le PV (en fonction de la préférence beta)
        uint256 pvContribution = (totalAvailablePVPower * uint256(prefs.beta)) / 100;
        pvContribution = pvContribution > demandWh ? demandWh : pvContribution;
        
        if (pvContribution > 0) {
            ev.consumedFromPV = pvContribution;
            demandWh -= pvContribution;
            totalAvailablePVPower -= pvContribution;
            
            // Mettre à jour la SOC de l'EV
            ev.soc += uint8((pvContribution * uint256(ev.efficiency)) / (ev.maxPower * 100));
            
            // Enregistrer le coût du PV
            uint256 pvCost = (pvContribution * hourlyPrices[currentHour].pvPrice) / 1000;
            agentCosts[evId].pvCost += pvCost;
            agentCosts[evId].totalCost += pvCost;
            
            emit EnergyAllocated(evId, findPVAgent(), pvContribution, hourlyPrices[currentHour].pvPrice);
        }
        
        // Allocation depuis le stockage (en fonction de la préférence gamma)
        if (demandWh > 0 && totalAvailableStoragePower > 0) {
            uint256 storageContribution = (totalAvailableStoragePower * uint256(prefs.gamma)) / 100;
            storageContribution = storageContribution > demandWh ? demandWh : storageContribution;
            
            if (storageContribution > 0) {
                ev.consumedFromStorage = storageContribution;
                demandWh -= storageContribution;
                totalAvailableStoragePower -= storageContribution;
                
                // Mettre à jour la SOC de l'EV
                ev.soc += uint8((storageContribution * uint256(ev.efficiency)) / (ev.maxPower * 100));
                
                // Enregistrer le coût du stockage
                uint256 storageCost = (storageContribution * hourlyPrices[currentHour].storagePrice) / 1000;
                agentCosts[evId].storageCost += storageCost;
                agentCosts[evId].totalCost += storageCost;
                
                emit EnergyAllocated(evId, findStorageAgent(), storageContribution, hourlyPrices[currentHour].storagePrice);
            }
        }
        
        // Allocation depuis le réseau (en fonction de la préférence alpha)
        if (demandWh > 0) {
            uint256 gridContribution = (demandWh * uint256(prefs.alpha)) / 100;
            
            ev.consumedFromGrid = gridContribution;
            
            // Mettre à jour la SOC de l'EV
            ev.soc += uint8((gridContribution * uint256(ev.efficiency)) / (ev.maxPower * 100));
            
            // S'assurer que SOC ne dépasse pas 100%
            if (ev.soc > 100) {
                ev.soc = 100;
            }
            
            // Enregistrer le coût du réseau
            uint256 gridCost = (gridContribution * hourlyPrices[currentHour].gridPrice) / 1000;
            agentCosts[evId].gridCost += gridCost;
            agentCosts[evId].totalCost += gridCost;
            
            emit EnergyAllocated(evId, findGridAgent(), gridContribution, hourlyPrices[currentHour].gridPrice);
        }
        
        // Émettre l'événement coût total calculé
        emit EnergyCostCalculated(evId, agentCosts[evId].totalCost);
    }

    /**
     * @dev Calcule le coût total pour un agent
     */
    function calculateTotalCost(uint256 agentId) public view returns (uint256) {
        return agentCosts[agentId].totalCost;
    }

    /**
     * @dev Traite un paiement entre agents
     */
    function processPayment(uint256 fromAgentId, uint256 toAgentId, uint256 amount) public onlyOwner {
        require(fromAgentId < agentCount && toAgentId < agentCount, "IDs d'agents invalides");
        
        // Logique de paiement - dans un environnement de production, utilisez des jetons ERC20
        // ou un mécanisme similaire. Ici, nous émettons simplement un événement.
        emit PaymentProcessed(fromAgentId, toAgentId, amount);
    }

    /**
     * @dev Trouve l'agent PV (on suppose qu'il n'y en a qu'un pour simplifier)
     */
    function findPVAgent() private view returns (uint256) {
        for(uint256 i = 0; i < agentCount; i++) {
            if(agents[i].agentType == AgentType.PV) {
                return i;
            }
        }
        revert("Aucun agent PV trouve");
    }

    /**
     * @dev Trouve l'agent stockage (on suppose qu'il n'y en a qu'un pour simplifier)
     */
    function findStorageAgent() private view returns (uint256) {
        for(uint256 i = 0; i < agentCount; i++) {
            if(agents[i].agentType == AgentType.Storage) {
                return i;
            }
        }
        revert("Aucun agent Stockage trouve");
    }

    /**
     * @dev Trouve l'agent réseau (on suppose qu'il n'y en a qu'un pour simplifier)
     */
    function findGridAgent() private view returns (uint256) {
        for(uint256 i = 0; i < agentCount; i++) {
            if(agents[i].agentType == AgentType.Grid) {
                return i;
            }
        }
        revert("Aucun agent Reseau trouve");
    }

    /**
     * @dev Retourne le compte total d'agents
     */
    function getAgentCount() public view returns (uint256) {
        return agentCount;
    }
}
