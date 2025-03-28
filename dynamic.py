import os
import re
import csv
import json
import time
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin

load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0'}
RELEVANT_KEYWORDS = [
    "about", "company", "history", "mission", "values", "ethics", "sustainability",
    "corporate", "leadership", "executives", "our story", "who we are", "governance",
    "team", "culture", "foundation", "commitment", "social responsibility", "impact",
    "our vision", "principles", "philosophy", "brand story", "heritage", "our legacy",
    "purpose", "csr", "initiatives", "innovation", "environment", "diversity",
    "inclusion", "careers", "investors", "locations", "where we are", "suppliers",
    "partners", "contact", "media", "news", "awards", "recognition"
]

def get_relevant_links(base_url):
    """Fetches relevant subpages from the homepage."""
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=10)
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

def scrape_combined_text(urls):
    """Scrapes and combines text from multiple pages."""
    combined_text = ""
    for url in urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(" ", strip=True)
            combined_text += f"\n--- Content from {url} ---\n{page_text}"
        except requests.RequestException as e:
            print(f"Skipping {url} due to error: {e}")
    return combined_text

def extract_company_details(text, website, retries=3):
    """Extracts company details using Gemini AI."""
    if not text:
        return ["No content available"] * 6

    prompt = f"""
    Extract the following details about {website} from the given text. 
    Ensure that each response is **detailed and accurate**, without extra commentary.

    1. **Mission Statement**: Clearly state the company's mission.
    2. **Products or Services**: List the main products or services the company provides.
    3. **Founded (Year & Founders)**: Mention the year of founding and names of the founders.
    4. **Headquarters Location**: Provide the city and country of the company's headquarters.
    5. **Key Executives**: List key executives such as CEO, CFO, and other leadership roles.
    6. **Notable Awards**: Mention any industry recognitions, notable awards, or achievements.

    Text: {text}

    Provide your response in the following format:
    1. Mission Statement: ...
    2. Products or Services: ...
    3. Founded (Year & Founders): ...
    4. Headquarters Location: ...
    5. Key Executives: ...
    6. Notable Awards: ...

    Respond **only** with the extracted details, no extra text.
    """
    
    model = genai.GenerativeModel("gemini-1.5-flash")

    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            matches = re.findall(r"\d+\.\s(.*)", response.text)

            if len(matches) == 6:
                return matches
        except Exception as e:
            print(f"AI error: {e}. Retrying in {2**attempt} sec...")
            time.sleep(2**attempt)

    return ["AI extraction failed"] * 6

def save_to_csv(data, filename="result2.csv"):
    """Saves extracted data to CSV."""
    file_exists = os.path.isfile(filename)

    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["Website", "Mission Statement", "Products or Services", "Founded", 
                             "Headquarters", "Key Executives", "Notable Awards"])
        
        for row in data:
            writer.writerow(row)

def main():
    websites = [
        "https://www.boeing.com/company",
            "https://www.goldmansachs.com",
    "https://corporate.exxonmobil.com",
    "https://www.hsbc.com",
    "https://www.volkswagenag.com",
    "https://www.ibm.com",
    "https://www.unilever.com"
    ]
    all_data = []

    for website in websites:
        print(f"Processing: {website}")
        
        relevant_links = get_relevant_links(website)
        if not relevant_links:
            print(f"No relevant links found for {website}")
            continue

        combined_text = scrape_combined_text(relevant_links)
        extracted_info = extract_company_details(combined_text, website)

        all_data.append([website] + extracted_info)
        time.sleep(2)

    save_to_csv(all_data)
    print("Data extraction completed. CSV updated.")

if __name__ == "__main__":
    main()
