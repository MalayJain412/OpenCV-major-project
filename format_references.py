import os
import re

def format_authors(authors_str):
    # Split by ' - '
    parts = authors_str.split(' - ')
    authors_part = parts[0].strip()
    # Split authors by comma
    author_list = [a.strip() for a in authors_part.split(',')]
    # Format to Last, First Initial.
    formatted = []
    for author in author_list:
        parts_auth = author.split()
        if len(parts_auth) >= 2:
            last = parts_auth[-1]
            initials = ''.join(p[0] + '.' for p in parts_auth[:-1])
            formatted.append(f"{last}, {initials}")
        else:
            formatted.append(author)
    if len(formatted) > 3:
        return formatted[0] + ' et al.'
    elif len(formatted) == 1:
        return formatted[0]
    else:
        return ', '.join(formatted[:-1]) + ', and ' + formatted[-1]

def format_title(title):
    # Clean title, remove extra spaces
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def format_reference(ref, index):
    title = format_title(ref['title'])
    authors = format_authors(ref['authors'])
    # Extract year and journal
    parts = re.split(r'\s*-\s*', ref['authors'])
    year = 'n.d.'
    journal = 'Preprint'
    if len(parts) >= 2:
        journal_year = parts[1].strip()
        # Journal year might be "Journal, year"
        if ',' in journal_year:
            j, y = journal_year.split(',', 1)
            journal = j.strip()
            year = y.strip()
        else:
            journal = journal_year
            if len(parts) >= 3:
                year = parts[2].strip()
    # Format as IEEE
    citation = f"[{index}] {authors}, \"{title},\" {journal}, {year}."
    return citation

# Load references from references.txt
references = []
with open(r'e:\OpenCV major project\sites\references.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Parse the content
blocks = content.split('\n\n')
for block in blocks:
    if block.strip():
        lines = block.split('\n')
        ref = {}
        for line in lines:
            if line.startswith('Title: '):
                ref['title'] = line[7:]
            elif line.startswith('Authors: '):
                ref['authors'] = line[9:]
            elif line.startswith('Link: '):
                ref['link'] = line[6:]
            elif line.startswith('Abstract: '):
                ref['abstract'] = line[10:]
        if ref:
            references.append(ref)

# Format and save
output_file = r'e:\OpenCV major project\sites\formatted_references.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("References\n\n")
    for i, ref in enumerate(references, 1):
        citation = format_reference(ref, i)
        f.write(citation + '\n')
        print(citation)