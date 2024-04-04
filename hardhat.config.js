/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  networks: {
    hardhat: {
      chainId: 2017,
      gasPrice: 0,
      initialBaseFeePerGas: 0,
      blockGasLimit: 800000000,
      hardfork: "merge",  // We should use "berlin", but because of the https://github.com/NomicFoundation/hardhat/issues/5052 issue we are using "merge".
      throwOnTransactionFailures: false,
      throwOnCallFailures: false,
      allowBlocksWithSameTimestamp: true
    },
  },
  solidity: "0.8.23",
};