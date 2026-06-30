import subprocess
from collections import Counter

def get_git_metrics(startpath):
    print("-> [GIT] Analyzing Provenance (Churn & Age)...")
    churn_map = Counter()
    age_map = {}
    author_map = {}

    try:
        raw_age = subprocess.check_output(['git', 'log', '--name-status', '--pretty=format:%at'], cwd=startpath, encoding='utf-8')
        curr_ts = None
        for line in raw_age.splitlines():
            if not line.strip(): continue
            if line[0].isdigit():
                curr_ts = int(line.strip())
            elif curr_ts:
                f = line.split('\t')[-1].replace('\\', '/')
                churn_map[f] += 1
                if f not in age_map: age_map[f] = curr_ts
        
        raw_authors = subprocess.check_output(['git', 'log', '--pretty=format:%an', '--name-only'], cwd=startpath, encoding='utf-8')
        curr_author = None
        file_authors = {} 
        for line in raw_authors.splitlines():
            if not line.strip(): continue
            if '|' not in line and '/' not in line and '.' not in line: 
                curr_author = line.strip()
            elif curr_author:
                f = line.strip().replace('\\', '/')
                if f not in file_authors: file_authors[f] = []
                file_authors[f].append(curr_author)
        
        for f, authors in file_authors.items():
            author_map[f] = Counter(authors).most_common(1)[0][0]
            
    except Exception as e:
        print(f"   [!] Git analysis failed: {e}")
        
    return churn_map, age_map, author_map
