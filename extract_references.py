import os
from bs4 import BeautifulSoup

def extract_references(html_file_path):
    with open(html_file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    references = []
    results = soup.find_all('div', class_='gs_r gs_or gs_scl')
    
    for result in results:
        title_elem = result.find('h3', class_='gs_rt')
        if title_elem:
            title_link = title_elem.find('a')
            if title_link:
                title = title_link.get_text(strip=True)
                link = title_link.get('href')
            else:
                title = title_elem.get_text(strip=True)
                link = None
        else:
            title = "No title"
            link = None
        
        authors_elem = result.find('div', class_='gs_a')
        if authors_elem:
            authors = authors_elem.get_text(strip=True)
        else:
            authors = "No authors"
        
        abstract_elem = result.find('div', class_='gs_rs')
        if abstract_elem:
            abstract = abstract_elem.get_text(strip=True)
        else:
            abstract = "No abstract"
        
        references.append({
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'link': link
        })
    
    return references

# Process both HTML files
sites_dir = r'e:\OpenCV major project\sites'
files = [
    'Real-Time Human Pose Estimation for Fitness, Surveillance... - Google Scholar.html',
    'Real-Time Human Pose Estimation for Fitness, Surveillance... - Google Scholar1.html'
]

all_references = []
for file in files:
    file_path = os.path.join(sites_dir, file)
    if os.path.exists(file_path):
        refs = extract_references(file_path)
        all_references.extend(refs)
        print(f"Extracted {len(refs)} references from {file}")
    else:
        print(f"File not found: {file_path}")

# Save to a text file with hyperlinks
output_file = os.path.join(sites_dir, 'references.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    for i, ref in enumerate(all_references, 1):
        f.write(f"Title: {ref['title']}\n")
        f.write(f"Authors: {ref['authors']}\n")
        f.write(f"Link: {ref['link']}\n")
        f.write(f"Abstract: {ref['abstract'][:300]}...\n\n")

print(f"Saved references to {output_file}")

# Also print to console
for i, ref in enumerate(all_references, 1):
    print(f"{i}. Title: {ref['title']}")
    print(f"   Authors: {ref['authors']}")
    if ref['link']:
        print(f"   Link: {ref['link']}")
    else:
        print("   Link: No link")
    print(f"   Abstract: {ref['abstract'][:200]}...")
    print()