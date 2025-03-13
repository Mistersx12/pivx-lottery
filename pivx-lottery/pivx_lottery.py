import requests
import re
import time
from decimal import Decimal

BLOCKBOOK_API_URL = "https://explorer.duddino.com/api/v2"
ENTRY_AMOUNT = Decimal('1.0')
REQUIRED_CONFIRMATIONS = 6  # Number of confirmations required

# Configurable settings
MAX_RETRIES = 100  # Limit the number of retries to avoid infinite loop
VERBOSE = False    # Set to True for detailed logs
MAX_RUNTIME = 3600  # Maximum runtime in seconds (1 hour)

target_block = 4811933
lottery_wallet = "D7PbXE9idKtpV355JS6DeU4BpRab5xhSLB"
specific_tx_hash = "b30ed421fca5f45edc411e555300c7bc451766d0d8a1dbb74d0c1ae8debb5b83"

def log(message):
    if VERBOSE:
        print(message)

def is_valid_transaction(tx, lottery_wallet):
    """Validate if transaction is relevant to the lottery."""
    outputs = tx.get("vout", [])
    for output in outputs:
        addresses = output.get("addresses", [])
        # Assuming value is in satoshis, convert to PIVX (1 PIVX = 1e8 satoshis)
        value_satoshis = Decimal(output.get("value", '0'))
        value_pivx = value_satoshis / Decimal('1e8')
        if lottery_wallet in addresses and value_pivx >= ENTRY_AMOUNT:
            return True
    return False

def get_latest_block():
    """Fetch the latest block height from Blockbook API."""
    retries = 0
    while retries < 5:
        try:
            response = requests.get(f"{BLOCKBOOK_API_URL}", timeout=10)
            response.raise_for_status()
            data = response.json()
            return int(data.get("blockbook", {}).get("bestHeight", 0))
        except Exception as e:
            log(f"❌ Error fetching latest block (attempt {retries + 1}): {e}")
            time.sleep(5)
            retries += 1
    return None

def get_block_hash(block_height):
    """Fetch the block hash for a specific block height."""
    retries = 0
    while retries < 5:
        try:
            response = requests.get(f"{BLOCKBOOK_API_URL}/block-index/{block_height}", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("blockHash", None)
        except Exception as e:
            log(f"❌ Error fetching block hash (attempt {retries + 1}): {e}")
            time.sleep(5)
            retries += 1
    return None

def get_winning_number(block_hash, participants):
    """Determine the winner based on the block hash."""
    if not participants:
        return None
    hash_int = int(block_hash, 16)
    winner_index = hash_int % len(participants) + 1
    return winner_index

def announce_winner(winner_index, participants, block_hash):
    """Announce the winner of the lottery with detailed information."""
    winner_tx = participants.get(winner_index, "UNKNOWN")
    print("🏆 Winner Details:")
    print(f"🎟️ Ticket #: {winner_index}")
    print(f"💸 TX ID: {winner_tx}")
    print(f"🔗 Block Hash Used: {block_hash}")
    print("🎉 Thank you all for participating!")

def fetch_lottery_entries(lottery_wallet, timeout=300):
    print(f"🔍 Checking transactions for wallet: {lottery_wallet}")

    participants = {}
    start_time = time.time()

    url = f"{BLOCKBOOK_API_URL}/address/{lottery_wallet}?details=txs"
    try:
        response = requests.get(url, timeout=10)
        log(f"📡 API Response Status Code: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        transactions = data.get("transactions", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return participants
    except ValueError:
        print("❌ Error parsing JSON response.")
        return participants

    if not transactions:
        print("⚠️ No transactions found for the lottery wallet.")
        return participants

    for tx in transactions:
        tx_hash = tx.get("txid", "UNKNOWN_HASH")
        confirmations = tx.get("confirmations", 0)
        log(f"Transaction Data: {tx}")

        if is_valid_transaction(tx, lottery_wallet):
            if confirmations >= REQUIRED_CONFIRMATIONS:
                if tx_hash not in participants.values():
                    entry_count = len(participants) + 1
                    participants[entry_count] = tx_hash
                    print(f"🎟️ {entry_count} ticket(s) entered the game with TX {tx_hash}")
            else:
                log(f"⚠️ Transaction {tx_hash} has only {confirmations} confirmations. Waiting for more.")
        else:
            print(f"❌ Transaction {tx_hash} is invalid or below the minimum entry amount.")

        if tx_hash == specific_tx_hash:
            print(f"✅ Specific transaction {specific_tx_hash} found with {confirmations} confirmations.")

    print(f"🎟️ FINAL PARTICIPANTS ({len(participants)} Total): {participants}")
    return participants

if __name__ == "__main__":
    print("🟣 Running PIVX Lottery System...")

    print(f"🔢 Using target block number: {target_block}")
    print(f"💼 Using lottery wallet address: {lottery_wallet}")

    start_time = time.time()
    participants = fetch_lottery_entries(lottery_wallet)

    if not participants:
        print("⚠️ No valid participants found. Lottery cannot proceed.")
    else:
        print("⏳ Waiting for the target block...")
        retries = 0
        while retries < MAX_RETRIES:
            if time.time() - start_time > MAX_RUNTIME:
                print("⏰ Maximum runtime reached. Exiting the lottery system.")
                break

            current_block = get_latest_block()
            if current_block is None:
                print("⚠️ Could not fetch the latest block. Retrying in 10 seconds...")
                time.sleep(10)
                retries += 1
                continue

            blocks_remaining = target_block - current_block
            if blocks_remaining > 0:
                if blocks_remaining <= 10:
                    print(f"🚨 Only {blocks_remaining} block(s) left! 🚨")
                else:
                    print(f"⏳ {blocks_remaining} block(s) left until the raffle block")
                time.sleep(30)
                retries += 1
            elif current_block >= target_block:
                print(f"🚀 Target block {target_block} reached! Proceeding with the raffle...")
                block_hash = get_block_hash(target_block)
                if block_hash:
                    winning_number = get_winning_number(block_hash, participants)
                    if winning_number is not None:
                        announce_winner(winning_number, participants, block_hash)
                    else:
                        print("⚠️ Could not determine a winner.")
                else:
                    print("⚠️ Failed to retrieve a valid block hash.")
                break
        else:
            print("⏰ Maximum retries reached. Exiting the lottery system.")
