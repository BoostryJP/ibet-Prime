/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  networks: {
    hardhat: {
      hardfork: "shanghai",
      chainId: 2025,
      gasPrice: 0,
      initialBaseFeePerGas: 0,
      throwOnTransactionFailures: false,
      throwOnCallFailures: false,
      allowBlocksWithSameTimestamp: true
    },
  },
  solidity: "0.8.23",
};