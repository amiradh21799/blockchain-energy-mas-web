const EnergyManagementSystem = artifacts.require("EnergyManagementSystem");

module.exports = function (deployer) {
  deployer.deploy(EnergyManagementSystem);
};
