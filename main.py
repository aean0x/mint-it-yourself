import subprocess
import sys
import os
import json
import re
import time

def check_contract_parameters():
    # Load user configuration
    try:
        with open('contract_parameters.json', 'r') as config_file:
            contract_parameters = json.load(config_file)
    except FileNotFoundError:
        print("Configuration file not found. Please make sure 'contract_parameters.json' exists and is filled out.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Configuration file is not valid JSON.")
        sys.exit(1)

    # Verify that the user provided all the necessary information
    required_keys = ['to_address', 'network_choice', 'token_name', 'token_symbol', 'contract_name', 'creator_earnings', 'gas_price']
    if not all(key in contract_parameters and contract_parameters[key] for key in required_keys):
        print("All configuration details must be provided in 'contract_parameters.json'.")
        sys.exit(1)

    # Validate Ethereum addresses
    if not is_valid_ethereum_address(contract_parameters['to_address']):
        print("Invalid Ethereum address for 'to_address'.")
        sys.exit(1)

    print("User configuration valid.")

def create_eth_env_file():
    env_file = '.env'
    infura_key_exists = False
    mnemonic_exists = False

    # Create the .env file if it doesn't exist
    if not os.path.exists(env_file):
        print("'.env' file not found. Creating a new one.")
        open(env_file, 'a').close()

    # Check if the keys exist in the .env file
    with open(env_file, 'r') as file:
        env_content = file.read()
        infura_key_exists = "INFURA_API_KEY=" in env_content
        mnemonic_exists = "MNEMONIC=" in env_content

    # Prompt for Infura API key if it doesn't exist
    if not infura_key_exists:
        infura_api_key = input("Enter your Infura API Key: ").strip()
        with open(env_file, 'a') as file:
            file.write(f"INFURA_API_KEY={infura_api_key}\n")
        print("Infura API key added to '.env' file.")
    else:
        print("Infura API key already exists in '.env' file.")

    # Prompt for Mnemonic if it doesn't exist
    if not mnemonic_exists:
        mnemonic = input("Enter your Mnemonic: ").strip()
        with open(env_file, 'a') as file:
            file.write(f"MNEMONIC={mnemonic}\n")
        print("Mnemonic added to '.env' file.")
    else:
        print("Mnemonic already exists in '.env' file.")

    if not (infura_key_exists and mnemonic_exists):
        print("Ethereum and API key configuration updated.")

def create_arweave_env_file():
    env_file = '.env'

    # Check if Arweave key already exists in the .env file
    if os.path.exists(env_file):
        with open(env_file, 'r') as file:
            if 'ARWEAVE_KEY' in file.read():
                print("\nArweave key already exists in '.env' file.\n")
                return

    print("\n\"image\" field in metadata is not a valid URL. Arweave Key required.")
    arweave_key_input = input("Enter your Arweave Key: ").strip()

    try:
        # Parse and then stringify the JSON object
        arweave_key_json = json.loads(arweave_key_input)
        arweave_key_str = json.dumps(arweave_key_json)
    except json.JSONDecodeError:
        print("Invalid JSON. Please make sure your Arweave Key is a valid JSON string.")
        return

    with open(env_file, 'a') as file:
        file.write(f"ARWEAVE_KEY='{arweave_key_str}'")

    print("Arweave key added to '.env' file.")

def get_network_id(network_name):
    network_ids = {
        "mainnet": "1",
        "goerli": "5",
        "sepolia": "11155111",
        # Add other networks as needed
    }
    return network_ids.get(network_name.lower())

def check_for_existing_contract(contract_name, network_id):
    artifact_path = f'./build/contracts/{contract_name}.json'
    try:
        with open(artifact_path, 'r') as artifact_file:
            artifact = json.load(artifact_file)
        contract_address = artifact.get('networks', {}).get(str(network_id), {}).get('address', None)
        if contract_address:
            return contract_address
        else:
            print("No existing contract found.")
            return None
    except (FileNotFoundError, KeyError):
        print("Contract artifact file not found or invalid.")
        return None

def isValidURL(url):
    # Simple URL validation
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def get_content_type(file_path):
    extension = file_path.split('.')[-1].lower()
    return {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'glb': 'model/gltf-binary',
        'gltf': 'model/gltf+json'
    }.get(extension, 'application/octet-stream')

def create_default_metadata(file_name, arweave_url=None):
    return {
        "name": f"NFT for {file_name}",
        "description": "A unique digital collectible asset.",
        "image": arweave_url if arweave_url else "None",  # We'll update this URL later
    }

def process_files(directory_path):
    supported_formats = ['jpg', 'png', 'gif', 'svg', 'mp4', 'webm', 'mp3', 'wav', 'ogg', 'glb', 'gltf']
    files_to_process = []

    for file in os.listdir(directory_path):
        file_ext = file.split('.')[-1].lower()
        metadata_needs_upload = False
        if file_ext in supported_formats:
            token_id = os.path.splitext(file)[0]
            if token_id.isdigit():
                metadata_file = f"{token_id}.json"
                metadata_path = os.path.join(directory_path, metadata_file)
                metadata = {}
                skip_upload = False
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as md_file:
                        metadata = json.load(md_file)
                    if 'image' in metadata and isValidURL(metadata['image']):
                        skip_upload = True  # Valid URL, skip upload
                    if 'image' not in metadata or not isValidURL(metadata['image']):
                        metadata_needs_upload = True
                else:
                    if input(f"\nMetadata \"{metadata_file}\" does not exist. Create boilerplate metadata? (y/n): ").strip().lower() == 'y':
                        # Create default metadata if JSON file does not exist
                        metadata = create_default_metadata(file, None)
                        metadata_needs_upload = True
                    else:
                        sys.exit(f"Metadata file for \"{metadata_file}\" not found. Please create a JSON file with the same name as the image file or remove the file from the images directory.")
                
                # Construct the full file path
                file_path = os.path.join(directory_path, file)
                content_type = get_content_type(file_path)
                files_to_process.append((file, int(token_id), metadata, skip_upload, content_type, metadata_needs_upload))

    return files_to_process

def check_node_npm():
    try:
        node_version = subprocess.check_output('node --version', shell=True).decode('utf-8').strip()
        npm_version = subprocess.check_output('npm --version', shell=True).decode('utf-8').strip()
        print(f"Node.js version: {node_version}, npm version: {npm_version}")
    except Exception as e:
        print(f"Error: {e}")
        print("Node.js and npm are required. Please install or ensure they are added to PATH.")
        print("See https://nodejs.org/en/download/.")

def install_npm_packages():
    # List of npm packages to install
    npm_packages = [
        "truffle",
        "@truffle/hdwallet-provider",
        "dotenv",
        "@openzeppelin/contracts@latest",
        "arweave"
    ]

    try:
        # Install all npm packages
        subprocess.check_call(f'npm install {" ".join(npm_packages)}', shell=True)
        print("Necessary npm packages installed successfully.")
    except Exception as e:
        print(f"Failed to install npm packages: {e}")
        sys.exit(1)

def check_npm_packages():
    # List of npm packages to check
    npm_packages = [
        {"name": "truffle", "command": "truffle version"},
        {"name": "@truffle/hdwallet-provider", "command": "npm list @truffle/hdwallet-provider"},
        {"name": "dotenv", "command": "npm list dotenv"},
        {"name": "@openzeppelin/contracts", "command": "npm list @openzeppelin/contracts"},
        {"name": "arweave", "command": "npm list arweave"}
    ]

    all_installed = True

    for package in npm_packages:
        try:
            # Check if each package is installed
            subprocess.check_output(package["command"], shell=True)
            print(f"{package['name']} is installed.")
        except Exception as e:
            print(f"{package['name']} not found: {e}")
            all_installed = False

    if not all_installed:
        print("Not all npm packages are installed. Installing missing packages now.")
        install_npm_packages()

def init_truffle_project():
    if not os.path.exists('truffle-config.js'):
        try:
            subprocess.check_call('truffle init', shell=True)
            print("New Truffle project initialized.")
        except Exception as e:
            print(f"Failed to initialize a new Truffle project: {e}")
            sys.exit(1)
    else:
        print("Truffle project already initialized.")

def overwrite_truffle_config(network_choice, gas_price):
    config_content = f"""
require('dotenv').config();
const HDWalletProvider = require('@truffle/hdwallet-provider');

// Construct network URL within the JavaScript context
const network_url = `https://{network_choice}.infura.io/v3/${{process.env.INFURA_API_KEY}}`;

module.exports = {{
    networks: {{
        {network_choice}: {{
            provider: () => new HDWalletProvider(process.env.MNEMONIC, network_url),
            network_id: '*', // Use '*' for any network (Wildcard)
            gas: 8000000,
            gasPrice: {gas_price},
            confirmations: 2,
            timeoutBlocks: 200,
            skipDryRun: true
        }},
        // Other network configurations can be added here
    }},

    // Set default mocha options here, use special reporters, etc.
    mocha: {{
        // timeout: 100000
    }},

    // Configure your compilers
    compilers: {{
        solc: {{
            version: '0.8.21', // Use the version of Solidity you prefer
            // Other compiler settings...
        }}
    }},

    // Truffle DB settings (optional)
    db: {{
        enabled: false
    }}
}};
"""

    with open('truffle-config.js', 'w') as file:
        file.write(config_content)
    print("truffle-config.js overwritten successfully.")

def is_valid_ethereum_address(address):
    # Ethereum addresses have 42 characters: '0x' followed by 40 hexadecimal characters
    return re.match(r'^0x[a-fA-F0-9]{40}$', address) is not None

def create_script_initial_migrations():
    migrations_script_content = """
const Migrations = artifacts.require("Migrations");

module.exports = function (deployer) {
    deployer.deploy(Migrations);
};
"""

    with open('./migrations/1_initial_migrations.js', 'w', encoding='utf-8') as file:
        file.write(migrations_script_content)
    print("Initial migrations script created successfully.")

def create_script_deploy_contracts(contract_name):
    deploy_script_content = f"""
const {contract_name} = artifacts.require("{contract_name}");

module.exports = function (deployer) {{
    deployer.deploy({contract_name});
    // Additional contracts can be deployed here
}};
"""

    with open('./migrations/2_deploy_contracts.js', 'w', encoding='utf-8') as file:
        file.write(deploy_script_content)
    print(f"Deployment script for {contract_name} created successfully.")

def create_script_mint(contract_name, to_address, token_data):
    # Ensure token_data is a non-empty list
    if not token_data or not isinstance(token_data, list):
        print("Error: token_data is not defined or not a list.")
        sys.exit(1)

    mint_script = f"""
const {contract_name} = artifacts.require('{contract_name}');

module.exports = async function(callback) {{
    const contractInstance = await {contract_name}.deployed();
    const tokenData = {json.dumps(token_data)};
    const toAddress = '{to_address}';
    for (const data of tokenData) {{
        try {{
            const tokenId = data.tokenId;
            const tokenMetadata = data.metadata;
            const tokenURI = JSON.stringify(tokenMetadata);

            console.log('Minting token id ', tokenId, ' to ', toAddress);
            const tx = await contractInstance.mint(toAddress, tokenId, tokenURI);

            // Log the transaction hash
            console.log('Transaction hash:', tx.tx, '\\n');
        }} catch (error) {{
            console.error('Failed to mint NFT:', error);
        }}
    }}
    callback();
}};
"""

    with open('mint.js', 'w') as file:
        file.write(mint_script)

def create_contract_token(token_name, token_symbol, contract_name, creator_earnings):
    contract_content = f"""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Royalty.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract {contract_name} is ERC721Royalty, Ownable {{
    mapping(uint256 => string) private _tokenURIs;
    constructor() ERC721("{token_name}", "{token_symbol}") Ownable(msg.sender) {{}}

    function mint(address to, uint256 tokenId, string memory newTokenURI) public onlyOwner {{
        _mint(to, tokenId);
        _tokenURIs[tokenId] = newTokenURI;
        _setTokenRoyalty(tokenId, msg.sender, {creator_earnings});
    }}

    function tokenURI(uint256 tokenId) public view override returns (string memory) {{
        require(ownerOf(tokenId) != address(0), "ERC721: query for nonexistent token");
        return _tokenURIs[tokenId];
    }}
}}
"""
    
    contracts_dir = './contracts'
    os.makedirs(contracts_dir, exist_ok=True)
    contract_file_path = os.path.join(contracts_dir, f'{contract_name}.sol')
    with open(contract_file_path, 'w', encoding='utf-8') as file:
        file.write(contract_content)
    print(f"Contract {contract_file_path} created successfully.")

def create_contract_migrations():
    contract_content = """
    // SPDX-License-Identifier: MIT
    pragma solidity >=0.4.21 <0.9.0;

    contract Migrations {
        address public owner;
        uint public last_completed_migration;

        modifier restricted() {
            require(msg.sender == owner, "This function is restricted to the contract's owner");
            _;
        }

        constructor() {
            owner = msg.sender;
        }

        function setCompleted(uint completed) public restricted {
            last_completed_migration = completed;
        }

        function upgrade(address new_address) public restricted {
            Migrations upgraded = Migrations(new_address);
            upgraded.setCompleted(last_completed_migration);
        }
    }
    """

    # Write the contract to a .sol file in the contracts directory
    contracts_dir = './contracts'
    os.makedirs(contracts_dir, exist_ok=True)  # Ensure the contracts directory exists
    contract_file_path = os.path.join(contracts_dir, 'Migrations.sol')

    with open(contract_file_path, 'w', encoding='utf-8') as file:
        file.write(contract_content)
    print(f"Migrations contract created successfully at {contract_file_path}")

def create_script_arweave(files_to_upload):
    files_with_types = [{"path": file_path, "type": content_type} for file_path, content_type in files_to_upload]

    arweave_script = f"""
const Arweave = require('arweave');
const fs = require('fs');
require('dotenv').config();

async function uploadImages(files) {{
    const arweave = Arweave.init({{ host: 'arweave.net', port: 443, protocol: 'https' }});

    let arweaveKey = JSON.parse(process.env.ARWEAVE_KEY);
    let uploaded = [];

    for (let fileInfo of files) {{
        try {{
            const data = fs.readFileSync(fileInfo.path);
            let transaction = await arweave.createTransaction({{ data: data }}, arweaveKey);
            transaction.addTag('Content-Type', fileInfo.type);
            await arweave.transactions.sign(transaction, arweaveKey);

            let uploader = await arweave.transactions.getUploader(transaction);
            while (!uploader.isComplete) {{
                await uploader.uploadChunk();
            }}
            uploaded.push({{file: fileInfo.path, id: transaction.id}});
        }} catch (error) {{
            console.error('Error uploading file:', fileInfo.path, error);
        }}
    }}
    return uploaded;
}}

uploadImages({json.dumps(files_with_types)}).then(uploaded => console.log(JSON.stringify(uploaded))).catch(console.error);
"""

    with open('upload_to_arweave.js', 'w') as file:
        file.write(arweave_script)

def upload_to_arweave(files_to_upload, images_directory):
    create_script_arweave(files_to_upload)
    
    try:
        arweave_output = subprocess.check_output(['node', 'upload_to_arweave.js']).decode('utf-8').strip()
        uploaded_info = json.loads(arweave_output)

        uploaded_urls = {}
        for info in uploaded_info:
            file_name = os.path.basename(info['file'])
            file_path = os.path.join(images_directory, file_name)
            arweave_url = f"https://arweave.net/{info['id']}"
            uploaded_urls[file_path] = arweave_url
            print("Uploaded", file_name, "to Arweave:", arweave_url)
        return uploaded_urls
    except Exception as e:
        print(f"Failed to upload to Arweave: {e}")
        sys.exit(1)

def deploy_contracts(network_choice):
    print("\nDeploying a new contract...\n")
    
    # Compile the contract using Truffle
    try:
        subprocess.check_call('truffle compile --all', shell=True)
        print("Compilation complete.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to compile contracts: {e}")
        sys.exit(1)
    
    # Deploy the contract to the blockchain using Truffle
    try:
        subprocess.check_call(f'truffle migrate --reset --network {network_choice}', shell=True)
        print("Contract has been deployed.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to deploy contracts: {e}")
        sys.exit(1)

def mint_nft(network_choice):
    try:
        subprocess.check_call(f'truffle exec mint.js --network {network_choice}', shell=True)
        print("NFT minting script executed.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to mint NFT: {e}")
        sys.exit(1)

def main():
    print("\nSetting up environment...\n")
    check_node_npm()
    check_npm_packages()
    init_truffle_project()

    # Set up Ethereum-related environment
    check_contract_parameters()    
    create_eth_env_file()

    # Load user configuration from JSON file
    with open('contract_parameters.json', 'r') as config_file:
        contract_parameters = json.load(config_file)

    # Extract relevant details from user configuration
    to_address = contract_parameters.get('to_address')
    network_choice = contract_parameters.get('network_choice').lower()
    network_id = get_network_id(network_choice)
    contract_name = contract_parameters.get('contract_name')
    token_name = contract_parameters.get('token_name')
    token_symbol = contract_parameters.get('token_symbol')
    creator_earnings = contract_parameters.get('creator_earnings')
    gas_price = contract_parameters.get('gas_price')

    # Determine the project root and check if images directory exists
    project_root = os.path.dirname(os.path.abspath(__file__))
    images_directory = os.path.join(project_root, 'images')
    if os.path.exists(images_directory):
        print(f"Images directory found at {images_directory}.")
    else:
        print(f"\nPlease create an images directory in project root and place the files you'd like to mint there.")
        sys.exit(1)

    # Process files and determine the need for Arweave upload
    files_to_process = process_files(images_directory)
    files_to_upload = [
        (os.path.join(images_directory, file), content_type) 
        for file, _, _, skip_upload, content_type, _ in files_to_process if not skip_upload
    ]
    filesnames_to_upload = [file for file, _, _, skip_upload, _, _ in files_to_process if not skip_upload]

    # Prepare token data for minting
    token_data = []
    for file_name, token_id, metadata, _, _, _ in files_to_process:
        token_data.append({'tokenId': token_id, 'metadata': metadata})

    # Set up Arweave environment if needed and upload files
    if files_to_upload:
        if input(f"\nConfirm Arweave upload for token images {filesnames_to_upload} (y/n): ").strip().lower() != 'y':
            sys.exit("Transaction cancelled by user.")
        create_arweave_env_file()
        uploaded_urls = upload_to_arweave(files_to_upload, images_directory)

        # Update metadata with Arweave URL if uploaded
        for file_name, token_id, metadata, _, _, _ in files_to_process:
            file_path = os.path.join(images_directory, file_name)
            if file_path in uploaded_urls:
                metadata['image'] = uploaded_urls[file_path]
            metadata_file_path = os.path.join(images_directory, f"{token_id}.json")
            with open(metadata_file_path, 'w') as md_file:
                json.dump(metadata, md_file, indent=4)

    # Confirm network choice
    if input(f"\nTransact on network \"{network_choice}\"? (y/n): ").strip().lower() != 'y':
        sys.exit("Transaction cancelled by user.")

    
    # Check for existing contract and deploy contracts as necessary
    existing_contract_address = check_for_existing_contract(contract_name, network_id)
    
    if existing_contract_address:
        use_existing = input(f"\nAn existing contract was found at {existing_contract_address}. Would you like to use it? (y/n): ").strip().lower()
        if use_existing != 'y':
            deploy_new_contract = True
        else:
            deploy_new_contract = False
    else:
        deploy_new_contract = True

    if deploy_new_contract:
        # Contract creation and deployment
        if input(f"\nDeploy new contract? (y/n): ").strip().lower() != 'y':
            sys.exit("Transaction cancelled by user.")
        print("\nGenerating contracts...\n")
        create_contract_token(token_name, token_symbol, contract_name, creator_earnings)
        create_contract_migrations()
        create_script_initial_migrations()
        create_script_deploy_contracts(contract_name)
        overwrite_truffle_config(network_choice, gas_price)
        print("\nTruffle scripts and Solidity contracts generated.\n")
        print("Deploying contracts in 10 seconds...\nWarning: This will be expensive. Press ctrl+c to exit. \n")
        time.sleep(10)
        deploy_contracts(network_choice)
    else:
        print("\nUsing existing contract.")

    # Minting NFTs
    print("\nMinting NFT(s)...\n")
    create_script_mint(contract_name, to_address, token_data)
    mint_nft(network_choice)

if __name__ == "__main__":
    main()