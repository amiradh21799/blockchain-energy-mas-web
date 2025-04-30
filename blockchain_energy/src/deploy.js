/**
 * Script de déploiement du contrat EnergyManagementSystem
 * À exécuter avec: node deploy.js
 */
const Web3 = require('web3');
const fs = require('fs');
const path = require('path');

// Configuration
const ganacheUrl = 'http://127.0.0.1:7545';
const contractBuildPath = path.join(__dirname, '../build/contracts/EnergyManagementSystem.json');

async function deployContract() {
    try {
        // Connexion à Ganache
        const web3 = new Web3(ganacheUrl);
        console.log('Connecté à Ganache');
        
        // Vérifier la connexion
        const accounts = await web3.eth.getAccounts();
        console.log(`Compte principal: ${accounts[0]}`);
        console.log(`Balance: ${web3.utils.fromWei(await web3.eth.getBalance(accounts[0]), 'ether')} ETH`);
        
        // Charger le contrat compilé
        if (!fs.existsSync(contractBuildPath)) {
            throw new Error(`Le fichier compilé n'existe pas: ${contractBuildPath}. Exécutez d'abord 'truffle compile'.`);
        }
        
        const contractJson = JSON.parse(fs.readFileSync(contractBuildPath, 'utf8'));
        const abi = contractJson.abi;
        const bytecode = contractJson.bytecode;
        
        // Créer une instance du contrat
        const energyContract = new web3.eth.Contract(abi);
        
        // Déployer le contrat
        console.log('Déploiement du contrat...');
        const deployTx = energyContract.deploy({
            data: bytecode,
            arguments: []
        });
        
        // Estimer le gaz nécessaire
        const gas = await deployTx.estimateGas({ from: accounts[0] });
        
        // Envoyer la transaction
        const deployedContract = await deployTx.send({
            from: accounts[0],
            gas: Math.min(6000000, gas * 1.2) // Ajouter une marge de sécurité
        });
        
        console.log(`Contrat déployé à l'adresse: ${deployedContract.options.address}`);
        
        // Sauvegarder l'adresse du contrat pour une utilisation ultérieure
        const deployInfoPath = path.join(__dirname, '../deployed_contract.json');
        fs.writeFileSync(
            deployInfoPath,
            JSON.stringify({
                address: deployedContract.options.address,
                network: 'ganache',
                deployedAt: new Date().toISOString()
            }, null, 2)
        );
        
        console.log(`Informations de déploiement sauvegardées dans: ${deployInfoPath}`);
        
        return deployedContract.options.address;
    } catch (error) {
        console.error('Erreur lors du déploiement:', error);
        process.exit(1);
    }
}

// Si le script est exécuté directement (et non importé)
if (require.main === module) {
    deployContract().then(address => {
        console.log(`\nContrat déployé avec succès à l'adresse: ${address}`);
        process.exit(0);
    });
}

module.exports = { deployContract };
