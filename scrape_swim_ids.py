"""Scrape swimmer IDs and names from SwimCloud team rosters"""

import requests
from bs4 import BeautifulSoup
import csv
import re
from typing import List, Tuple


def scrape_roster_page(url: str) -> List[Tuple[str, str]]:
    """
    Scrape swimmer names and IDs from a SwimCloud roster page
    
    Args:
        url: The roster page URL
        
    Returns:
        List of tuples (name, swimmer_id)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    swimmers = []
    
    # Find swimmer rows in the roster table
    rows = soup.find_all('tr')
    
    for row in rows:
        # Look for links that point to swimmer profiles
        swimmer_link = row.find('a', href=re.compile(r'/swimmer/\d+'))
        
        if swimmer_link:
            name = swimmer_link.get_text(strip=True)
            
            # Extract swimmer ID from URL
            href = swimmer_link.get('href', '')
            match = re.search(r'/swimmer/(\d+)', href)
            
            if match:
                swimmer_id = match.group(1)
                swimmers.append((name, swimmer_id))
                print(f"Found: {name} (ID: {swimmer_id})")
    
    return swimmers


def scrape_all_pages(base_url: str, max_pages: int = None, output_file: str = "swimmers.csv") -> List[Tuple[str, str]]:
    """
    Scrape all pages of a roster with pagination
    
    Args:
        base_url: Base URL (with page=1)
        max_pages: Maximum pages to scrape (None for all)
        output_file: File to save results to after each page
        
    Returns:
        List of tuples (name, swimmer_id)
    """
    all_swimmers = []
    page = 1
    
    while True:
        # Replace page parameter
        url = re.sub(r'page=\d+', f'page={page}', base_url)
        
        print(f"\nScraping page {page}...")
        
        try:
            swimmers = scrape_roster_page(url)
            
            if not swimmers:
                print(f"No swimmers found on page {page}, stopping")
                break
            
            all_swimmers.extend(swimmers)
            
            # Save after each page to preserve progress
            save_to_csv(all_swimmers, output_file)
            
            page += 1
            
            if max_pages and page > max_pages:
                break
                
        except requests.RequestException as e:
            print(f"Error scraping page {page}: {e}")
            break
    
    return all_swimmers


def save_to_csv(swimmers: List[Tuple[str, str]], filename: str = "swimmers.csv") -> None:
    """
    Save swimmer data to CSV file
    
    Args:
        swimmers: List of (name, id) tuples
        filename: Output CSV filename
    """
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Swimmer ID'])
        writer.writerows(swimmers)
    
    print(f"\nSaved {len(swimmers)} swimmers to {filename}")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    team_id = "405"  # Default to Pitt
    gender = "M"  # Default to men
    
    # Check for team_id and gender arguments
    if len(sys.argv) > 1:
        # First arg could be team_id (if numeric) or gender
        if sys.argv[1].isdigit():
            team_id = sys.argv[1]
            if len(sys.argv) > 2:
                if sys.argv[2].lower() in ["women", "w", "female", "f"]:
                    gender = "F"
                elif sys.argv[2].lower() in ["men", "m", "male"]:
                    gender = "M"
        elif sys.argv[1].lower() in ["women", "w", "female", "f"]:
            gender = "F"
        elif sys.argv[1].lower() in ["men", "m", "male"]:
            gender = "M"
    
    # URL from the request
    base_url = f"https://www.swimcloud.com/team/{team_id}/roster/?page=1&gender={gender}&season_id=29&sort=perf"
    
    gender_name = "Women" if gender == "F" else "Men"
    print(f"Starting scrape of SwimCloud roster ({gender_name})...")
    print(f"URL: {base_url}\n")
    
    # Scrape first page only
    output_file = f"{'F' if gender == 'F' else 'M'}_swimmers.csv"
    swimmers = scrape_all_pages(base_url, max_pages=1, output_file=output_file)
    
    if swimmers:
        # Final summary
        print(f"\nTotal swimmers: {len(swimmers)}")
        print("First 5:")
        for name, swimmer_id in swimmers[:5]:
            print(f"  {name}: {swimmer_id}")
    else:
        print("No swimmers found!")
