# Mint it yourself!

## Overview
This Python program automates the process of minting and deploying Non-Fungible Tokens (NFTs) on Ethereum blockchain networks. It supports transactions on Ethereum mainnet, Goerli, and Sepolia testnets. The program creates necessary environmental files, validates and processes NFT data, handles contract deployment, and mints NFTs based on user input and configurations.

## Requirements
- **Node.js and npm**: Necessary for executing blockchain transactions and script operations.
- **Python 3**: For running the main script.
- **Ethereum Wallet**: A funded Ethereum wallet is required for handling transactions.
- **Arweave Wallet**: A funded Arweave wallet is required for hosting token images.
- **Contract Parameters**: User must provide a JSON configuration file (`contract_parameters.json`) with specific contract details.
- **NFT Images and Metadata**: Images to be minted as NFTs should be named as numbers (e.g., `1.jpg`) in the `images` directory. Corresponding metadata in JSON format should be named similarly (e.g., `1.json`).

## Configuration
### Ethereum and Arweave Keys
- Create `.env` file in the project root directory.
- Add Ethereum wallet's mnemonic and Infura API key.
- Add Arweave wallet key for image and metadata storage.

### Contract Parameters
Provide a JSON file named `contract_parameters.json` in the project root with the following structure:
```json
{
    "to_address": "0xYourEthereumAddress",
    "network_choice": "sepolia",  // Or "goerli" or "mainnet"
    "contract_name": "YourContractName",
    "token_name": "YourTokenName",
    "token_symbol": "YourTokenSymbol",
    "creator_earnings": "CreatorEarningsPercentage", // In basis points so 100 = 1%
    "gas_price": "GasPriceInWei"
}
```

## Usage
1. Place your NFT files in the `images` directory and create metadata jsons as necessary.
2. Run `python main.py` to start the program.
3. Follow the prompts to set up the environment, deploy contracts, and mint NFTs.

## Features
- **Validation**: Checks if all necessary configurations and files are present and valid.
- **Contract Deployment**: Deploys a new contract or uses an existing one based on user choice.
- **NFT Minting**: Automates the minting process of NFTs with provided metadata and images.
- **Network Support**: Capable of transacting on Ethereum mainnet and testnets (Goerli, Sepolia).

## Important Notes
- Ensure that your Ethereum wallet is sufficiently funded to cover gas fees.
- Arweave wallet should have a balance for image and metadata storage.
- The program will prompt for missing environment details.
- It's essential to review and confirm transactions, especially when transacting on the mainnet due to the involved costs.
- Pick a wise gas fee, because this can get really expensive, really fast.

## Disclaimer
Use this script at your own risk. I am not responsible for any financial losses or issues arising from the use of this script. Always test on testnets before using the mainnet.

I wrote this after determining that there were no practical solutions for easy self-deployment to the Ethereum blockchain. The original purpose of this was to get my avatar on the chain without any watermarks. Everything on my own wallet. Cost is no object. And that's what this script does. Anyway, don't expect me to continue support of this, but here it is for reference.