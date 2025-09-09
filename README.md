# Phoenix Dev

More info:  
[Telegram Channel](https://t.me/phoenix_w3)  
[Telegram Chat](https://t.me/phoenix_w3_space)

[Инструкция на русcком](https://phoenix-14.gitbook.io/phoenix/proekty/irys)</br>


## Irys
Irys is a blockchain protocol focused on data availability, ensuring that information published on-chain is accessible, verifiable, and permanent. It provides fast, scalable infrastructure that supports decentralized applications and AI systems


## Functionality
- Sprite type (max 1000 games)
- Galxe register
- Bridge to Gravity network for claim on Galxe
- Galxe claim Sprite type


## Requirements
- Python version 3.10 - 3.12 
- Private keys EVM
- Captcha [Capmonster](https://dash.capmonster.cloud/) for Galxe claim
- Proxy (optional)



## Installation
1. Clone the repository:
```
git clone https://github.com/Phoenix0x-web3/irys.git
cd irys
```

2. Install dependencies:
```
python install.py
```

3. Activate virtual environment: </br>

`For Windows`
```
venv\Scripts\activate
```
`For Linux/Mac`
```
source venv/bin/activate
```

4. Run script
```
python main.py
```

## Project Structure
```
irys/
├── data/                   #Web3 intarface
├── files/
|   ├── logs/               # Logs
|   ├── private_keys.txt    # Private keys EVM
|   ├── proxy.txt           # Proxy addresses (optional)
|   ├── reserve_proxy.txt   # Reserve proxy addresses (optional)
|   ├── wallets.db          # Database
│   └── settings.yaml       # Main configuration file
├── functions/              # Functionality
└── utils/                  # Utils
```
## Configuration

### 1. files folder
- `private_keys.txt`: Private keys EVM
- `proxy.txt`: One proxy per line (format: `http://user:pass@ip:port`)
- `reserve_proxy.txt`: One proxy per line (format: `http://user:pass@ip:port`)

### 2. Main configurations
```yaml
#Settings for the application

# Whether to encrypt private keys
private_key_encryption: true

# Number of threads to use for processing wallets
threads: 1

#BY DEFAULT: [0,0] - all wallets
#Example: [2, 6] will run wallets 2,3,4,5,6
#[4,4] will run only wallet 4
range_wallets_to_run: [0, 0]

# Whether to shuffle the list of wallets before processing
shuffle_wallets: true

# Working only if range_wallet_to_run = [0,0] 
# BY DEFAULT: [] - all wallets 
# Example: [1, 3, 8] - will run only 1, 3 and 8 wallets
exact_wallets_to_run: []

# Show wallet address in logs
show_wallet_address_log: false

#Check for github updates
check_git_updates: true

# the log level for the application. Options: DEBUG, INFO, WARNING, ERROR
log_level: INFO

# Delay before running the new cicle of wallets after it has completed all actions (1 - 2 hrs default)
random_pause_wallet_after_completion:
  min: 3600
  max: 7200

# Long Delay with 20% chance before running the same wallet again after it has completed all actions (4 - 8 hrs default)
random_pause_wallet_long_delay:
  min: 14400
  max: 28800

# Random pause between actions in seconds
random_pause_between_actions:
  min: 30
  max: 120

# Random pause between start wallets in seconds
random_pause_start_wallet:
  min: 0
  max: 0

#Perform automatic replacement from proxy reserve files
auto_replace_proxy: true

# Api Key from https://dash.capmonster.cloud/
capmonster_api_key: ""

#Network can use for bridge to Gravity, for Galxe quests. Available: ethereum, arbitrum, base, optimism, ink, mode, bsc, op_bnb, polygon, soneium, lisk, unichain, avalanche, zksync 
network_for_bridge: [arbitrum, optimism, base]
random_eth_for_bridge:
  min: 0.000025
  max: 0.0001
```

## Usage

For your security, you can enable private key encryption by setting `private_key_encryption: true` in the `settings.yaml`. If set to `false`, encryption will be skipped.

On first use, you need to fill in the `private_keys.txt` file once. After launching the program, go to `DB Actions → Import wallets to Database`.
<img src="https://imgur.com/5gxa66n.png" alt="Preview" width="600"/>

If encryption is enabled, you will be prompted to enter and confirm a password. Once completed, your private keys will be deleted from the private_keys.txt file and securely moved to a local database, which is created in the files folder.

<img src="https://imgur.com/2J87b4E.png" alt="Preview" width="600"/>

If you want to update proxy/twitter/discord/email you need to make synchronize with DB. After you made changes in these files, please choose this option.

<img src="https://imgur.com/lXT6FHn.png" alt="Preview" width="600"/>

Once the database is created, you can start the project by selecting `Irys → Run All Activities`.

<img src="https://imgur.com/nvYamqd.png" alt="Preview" width="600"/>





