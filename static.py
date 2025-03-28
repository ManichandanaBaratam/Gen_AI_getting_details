import os
import re
import json
import time
import requests
import pandas as pd
import google.generativeai as genai
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv


load_dotenv()
genai_api_key = os.getenv("GENAI_API_KEY")

if not genai_api_key:
    raise ValueError(" API key missing! Add GEMINI_API_KEY to your .env file.")

genai.configure(api_key=genai_api_key)

websites = [
    "https://www.goldmansachs.com",
    "https://corporate.exxonmobil.com",
    "https://www.hsbc.com",
    "https://www.volkswagenag.com",
    "https://www.ibm.com",
    "https://www.unilever.com"
]

RELEVANT_KEYWORDS = [
    "about", "company", "history", "mission", "values", "ethics", "sustainability",
    "corporate", "leadership", "executives", "our story", "who we are", "governance",
    "team", "culture", "foundation", "commitment", "social responsibility", "impact",
    "our vision", "principles", "philosophy", "brand story", "heritage", "our legacy",
    "purpose", "csr", "initiatives", "innovation", "environment", "diversity",
    "inclusion", "careers", "investors", "locations", "where we are", "suppliers",
    "partners", "contact", "media", "news", "awards", "recognition"
]

session = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Step 1: Extract Relevant Links from Homepage
def get_relevant_links(base_url):
    try:
        response = session.get(base_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch {base_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    relevant_links = set()
    for link in soup.find_all("a", href=True):
        full_url = urljoin(base_url, link["href"])
        if any(keyword in full_url.lower() for keyword in RELEVANT_KEYWORDS):
            relevant_links.add(full_url)

    return list(relevant_links)

# Step 2: Scrape and Combine Text Content
def scrape_combined_text(urls):
    combined_text = ""
    for url in urls:
        try:
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(" ", strip=True)
            combined_text += f"\n--- Content from {url} ---\n{page_text}"
        except requests.HTTPError as e:
            if response.status_code == 403:
                print(f"Skipping {url} (403 Forbidden)")
            else:
                print(f"Skipping {url} due to error: {e}")
        except requests.RequestException as e:
            print(f"Skipping {url} due to error: {e}")
    return combined_text

# Step 3: Extract Data Using AI with Retry Logic
def extract_company_details(text, website, retries=3):
    if not text:
        return {"error": "No content available"}

    prompt = f"""
    Extract key company details from the following text about {website}.
    Return the response as a structured JSON object:
    
    Text: {text}
    
    Respond only with valid JSON:
    {{
        "mission_statement": "...",
        "products_or_services": "...",
        "founded": "...",
        "headquarters": "...",
        "key_executives": "...",
        "notable_awards": "..."
    }}
    """

    model = genai.GenerativeModel("gemini-1.5-flash")

    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            if "429" in str(e):  
                wait_time = 2 ** attempt  
                print(f"Gemini AI rate limit hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Gemini AI error:", e)
                return {"error": "Gemini AI request failed"}

    return {"error": "Gemini AI rate limit exceeded"}

# Step 4: Run the Extraction Process and Save to CSV
def main():
    all_data = []

    for website in websites:
        print(f"Processing: {website}")
    
        relevant_links = get_relevant_links(website)
        if not relevant_links:
            print(f"No relevant links found for {website}")
            continue

        combined_text = scrape_combined_text(relevant_links)
        company_data = {"Website": website}
        extracted_data = extract_company_details(combined_text, website)
        company_data.update(extracted_data)

        all_data.append(company_data)

        time.sleep(2)  

    new_df = pd.DataFrame(all_data)

    csv_filename = "result.csv"
    new_df.to_csv(csv_filename, index=False, encoding="utf-8")

    print(f"Data saved to '{csv_filename}'.")

if __name__ == "__main__":
    main()
