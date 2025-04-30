/**
 * Configuration Truffle pour le déploiement de contrats
 * sur Ganache et autres réseaux
 */
module.exports = {
  networks: {
    // Réseau de développement local Ganache
    development: {
      host: "127.0.0.1",
      port: 7545,
      network_id: "5777", // ID du réseau Ganache
      gas: 6721975,       // Limite de gaz par défaut
      gasPrice: 20000000000 // 20 gwei
    },
    
    // Vous pouvez ajouter d'autres réseaux ici (testnet, mainnet, etc.)
  },

  // Configuration du compilateur Solidity
  compilers: {
    solc: {
      version: "0.8.19",    // Version du compilateur Solidity
      settings: {
        optimizer: {
          enabled: true,    // Optimisation activée
          runs: 200         // Optimiser pour 200 exécutions
        }
      }
    }
  },
  
  // Configuration des plugins (optionnel)
  plugins: [
    // "truffle-contract-size" // Décommentez pour voir la taille des contrats
  ]
};
