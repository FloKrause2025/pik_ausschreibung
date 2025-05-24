import requests
from bs4 import BeautifulSoup
from datetime import datetime
import schedule
import time

def send_to_slack(message):
    webhook_url = "https://hooks.slack.com/services/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"  # ← your webhook URL
    payload = {"text": message}
    requests.post(webhook_url, json=payload)


def scrape_and_safe ():
    url = "https://cryptogamblingnow.com"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    links = soup.find_all('a')

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"new_external_test_file_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as file:
        for i, link in enumerate(links, start=1):
            href = link.get('href')
        
            if href and href.startswith('http'):
                text = link.text.strip()
                file.write(f"{text} -> {href}\n")
    
    print(f"✅ Saved {filename}")
    send_to_slack(f"✅ Agent run and saved {filename}")

schedule.every(1).minute.do(scrape_and_safe)

print('Agent runs in 1 min...')

while True:
    schedule.run_pending()
    time.sleep(5)