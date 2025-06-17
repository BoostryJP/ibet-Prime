/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  networks: {
    hardhat: {
      hardfork: "shanghai",
      chainId: 2025,
      throwOnTransactionFailures: false,
      throwOnCallFailures: false,
      allowBlocksWithSameTimestamp: true,
      accounts: [
        {
            privateKey: "0x26c27bb6c4b42114f246bbf60c98adabddd28c7d80ec99da3efcb16860af9cee",
            balance: "10000000000000000000000" // 10,000 ETH
        },
        {
            privateKey: "0x603e7e39059fa842f9ba0a5a1689c8d616e8e628d6e7a591bd863d7565d2272c",
            balance: "10000000000000000000000" // 10,000 ETH
        },
        {
            privateKey: "0xdbe67c7bf8bec4baeea7af1a1c5ddfe0bdd05bf31ebd9e014c544d2cf8305941",
            balance: "10000000000000000000000" // 10,000 ETH
        },
        {
            privateKey: "0x265ead0ba105301cb7b13831aa179a5ba9259b33aedefbbb8c4a174d04e3bea7",
            balance: "10000000000000000000000" // 10,000 ETH
        },
        {
            privateKey: "0x172a71a1445958933c244c9b65b90c74f39b91661efedb6e961aa12d42c7330d",
            balance: "10000000000000000000000" // 10,000 ETH
        }
      ]
    },
  },
  solidity: "0.8.23",
};