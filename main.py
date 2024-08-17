import json
import time
import tls_client
from concurrent.futures import ThreadPoolExecutor, as_completed

skipWallets = False
skippedWallets = 0

# Initialize tls_client session
session = tls_client.Session(
    client_identifier="chrome_105",
    random_tls_extension_order=True
)

choice = input("[❓] Skip wallets with no 7d or 30d PnL data (Y/N): ")

if choice.lower() not in ["y", "n"]:
    skipWallets = False
elif choice.lower() == "y":
    skipWallets = True
else:
    skipWallets = False

print(f"[🤖] Set skip wallets to {skipWallets}")

try:
    threads = int(input("[❓] Threads: "))
except Exception:
    threads = 15

print(f"[🤖] Set threads to {threads}")

shorten = lambda s: f"{s[:4]}...{s[-5:]}" if len(s) >= 9 else "?"

with open('wallets.txt', 'r') as f:
    wallets = f.read().splitlines()
    print(f"[✅] Successfully grabbed {len(wallets)} wallets")

def getWalletData(wallet: str):
    global skippedWallets

    walletEndpoint = f"https://gmgn.ai/defi/quotation/v1/smartmoney/sol/walletNew/{wallet}?period=7d"
    response = session.get(walletEndpoint)

    if response.status_code == 200:
        data = response.json()
        
        if data['msg'] == "success":
            data = data['data']
            try:
                if data['pnl_7d'] != 0 or data['pnl_30d'] != 0:
                    directLink = f"https://gmgn.ai/sol/address/{wallet}"
                    totalProfitPercent = f"{data['total_profit_pnl'] * 100:.2f}%"
                    realizedProfit7dUSD = f"${data['realized_profit_7d']:,.2f}"
                    realizedProfit30dUSD = f"${data['realized_profit_30d']:,.2f}"
                    winrate_7d = f"{data['winrate'] * 100:.2f}%" if data['winrate'] is not None else "?"
                    winrate_30data = session.get(f"https://gmgn.ai/defi/quotation/v1/smartmoney/sol/walletNew/{wallet}?period=30d").json()['data']
                    winrate_30d = f"{winrate_30data['winrate'] * 100:.2f}%" if winrate_30data['winrate'] is not None else "?"
                    
                    try:
                        tags = data['tags'] 
                    except Exception:
                        tags = "?"
                    
                    return {
                        "wallet": wallet,
                        "totalProfitPercent": totalProfitPercent,
                        "7dUSDProfit": realizedProfit7dUSD,
                        "30dUSDProfit": realizedProfit30dUSD,
                        "winrate_7d": winrate_7d,
                        "winrate_30d": winrate_30d,
                        "tags": tags,
                        "directLink": directLink
                    }
                else:
                    if skipWallets:
                        skippedWallets += 1
                        print(f"[🤖] Skipped {skippedWallets} wallets", end="\r")
                        return None
                        
                    else:
                        directLink = f"https://gmgn.ai/sol/address/{wallet}"
                        return {
                            "wallet": wallet,
                            "directLink": directLink,
                            "tags": ["Skipped"]
                        }

            except Exception as e:
                print(f"{e} - {wallet}")
    return None

results = []

startTime = time.time()

with ThreadPoolExecutor(max_workers=threads) as executor:
    futures = {executor.submit(getWalletData, wallet): wallet for wallet in wallets}
    for future in as_completed(futures):
        result = future.result()
        if result is not None:
            results.append(result)
endTime = time.time()
totalTime = endTime - startTime

result_dict = {}

for result in results:
    maker = result.pop('wallet')
    result_dict[maker] = result

totalRequests = len(wallets)
requestsSec = totalRequests / totalTime

identifier = shorten(list(result_dict)[0])

with open(f'walletData_{identifier}.json', 'w') as outfile:
    json.dump(result_dict, outfile, indent=4)
    print(f"[✅] Dumped profit data for {len(result_dict)} wallet(s) | Requests/Sec: {requestsSec:.2f} | Time Taken: {totalTime:.2f}s | File Identifier: {identifier}")
