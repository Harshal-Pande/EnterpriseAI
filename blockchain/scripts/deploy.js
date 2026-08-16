const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const EnterpriseAudit = await hre.ethers.getContractFactory("EnterpriseAudit");
  const audit = await EnterpriseAudit.deploy();

  await audit.waitForDeployment();

  const address = await audit.getAddress();
  console.log(`EnterpriseAudit deployed to: ${address}`);

  // Save the address and ABI to a file for the backend to use
  const contractData = {
    address: address,
    abi: JSON.parse(audit.interface.formatJson())
  };

  const artifactPath = path.join(__dirname, '..', '..', 'backend', 'contract_data.json');
  fs.writeFileSync(artifactPath, JSON.stringify(contractData, null, 2));
  console.log(`Contract data saved to ${artifactPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
