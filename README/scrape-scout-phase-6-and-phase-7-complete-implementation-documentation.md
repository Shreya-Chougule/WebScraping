# ScrapeScout: Phase 6 & Phase 7 Implementation

# Documentation

# Executive Summary

## This document provides a comprehensive technical reference for the implementation of Phase

## 6 (Relevance Classification) and Phase 7 (Duplicate Detection & Resolution) of the

## ScrapeScout project. It includes complete module source code, unit test implementations,

execution instructions, and integration workflows.

# 1\. Project Overview & Architecture

## ScrapeScout is a freelance project discovery tool designed to scrape, extract, standardize,

classify, deduplicate, and store web/app development project listings.

# End-to-End Pipeline Workflow:

1\.​Data Collection (Phase 4): Scrape raw listings using BeautifulSoup & Playwright.

## 2\.​Standardization (Phase 5): Standardize data schemas (title, description,

budget, original\_url, etc.).

## 3\.​Relevance Classification (Phase 6): Filter irrelevant projects and classify relevant ones

into Web, App, Software, Both, or Other.

## 4\.​Duplicate Detection (Phase 7): Perform multi-tier check (URL, Content Hash, Fuzzy

Match) to filter out redundant listings. 5.​Database Storage: Map clean entities and store them into Supabase (PostgreSQL). 6.​Frontend Dashboard: Render real-time project metrics and feeds in the React UI.

# 2\. Phase 6: Relevance Classification (classifier.py)

# Technical Overview

## classifier.py evaluates project titles, descriptions, and technology stacks using keyword

heuristics to assign a project category and calculate a confidence score ($0.0$ to $1.0$).

# Source Code: backend/src/classifier.py

Python‎ import re from typing import List, Optional, Tuple

class ProjectClassifier: def \_\_init\_\_(self): self.web\_keywords = {"web","website","frontend",

""react"vue","node""angular","laravel,","tail-wind,","wordpress",

}self.app\_keywords = {"mobile""ios","android","app","kotlin","swift,","xamarin",

}self.software\_keywords = {"c++","c#","desktop""java","electron,","qt","system architecture",

}self.irrelevant\_keywords = {"content writer""copywriting""graphic designer,","logo design, }

def classify( self, title: str,""

, description: Optional\[str\] = technologies: Optional\[List\[str\]\] = None ) -\> Tuple\[str, float, bool\]:"""

Classifies a project into Web, App, Software, Both, or Other. R eturns: (category, confidence\_score, is\_relevant)"""

text = f"{title} {description or'' \[\])}".lower ()

\# Check for immediate irrelevance f or irr in self.irrelevant\_keywords: if irr in text:

r eturn"Other", 0.9, False

w eb\_count = sum(1 for kw in self.web\_keywords if re.search(r'\\b' re.escape(kw) + r'\\b', text)) app\_count = sum(1 for kw in self.app\_keywords if re.search(r'\\b' re.escape(kw) + r'\\b', text))

"backend","fullstack","full-stack"

"html","css","flask,","django","tailwind","express"

""flutter","react native ,

"cordova","ionic"

"automation","python script","embedded"

"seo article""blog writer",""virtual assistant" ,"data entry,",

' } {' .join(technologies or

\+

\+

\+ sw\_count = sum(1 for kw in self.software\_keywords if re.search(r'\\b' re.escape(kw) + r'\\b', text))

total\_matches = web\_count + app\_count + sw\_count

if total\_matches == 0:

r eturn"Other", 0.3, False

confidence = min(1.0, 0.5 + (total\_matches \* 0.15))

if w eb\_count \> 0 and app\_count \> 0: r eturn"Both", confidence, True elif web\_count \>= app\_count and web\_count \>= sw\_count: r eturn"Web", confidence, True elif app\_count \>= sw\_count: r eturn"App", confidence, True else:

r eturn"Software", confidence, True

# 3\. Phase 7: Duplicate Detection & Resolution

# (deduplicator.py)

# Technical Overview

## deduplicator.py runs a 3-tier matching process:

1\.​Exact URL Check: Direct string matching on original\_url. 2.​Content Hash Check: MD5 hash matching on normalized title + description.

## 3\.​Fuzzy Similarity Check: Levenshtein ratio evaluation using rapidfuzz ($threshold \\ge

85\.0%$).

# Source Code: backend/src/deduplicator.py

Python‎ import hashlib from typing import List, Optional, Tuple from rapidfuzz import fuzz

class ProjectDeduplicator: def \_\_init\_\_(self, similarity\_threshold: float = 85.0): self.similarity\_threshold = similarity\_threshold def generate\_content\_hash(self, title: str, description: Optional\[str\] = -\> str:

""" Generate an MD5 hash based on normalized title and description. n ormalized\_text = f"{title.strip().lower()} {description.strip().lower() if description else''}" n ormalized\_text ="

r eturn hashlib.md5(normalized\_text.encode("utf-8")).hexdigest()

def is\_duplicate( self, n ew\_project: dict, existing\_projects: List\[dict\] ) -\> Tuple\[bool, Optional\[str\]\]:"""

Checks if a project is a duplicate based on: 1 . Exact URL match

2 . Content Hash match

3\. Fuzzy Text Similarity match"""

n ew\_url = new\_project.get("original\_url", n ew\_title = new\_project.get("title", n ew\_desc = new\_project.get("description)", n ew\_hash = self.generate\_content\_hash(new\_title, new\_desc)

f or existing in existing\_projects: # 1 . Exact URL Check existing\_url = existing.get("original\_url", if n ew\_url and existing\_url and new\_url == existing\_url: r eturn True,"Duplicate URL match"

\# 2 . Content Hash Check existing\_hash = existing.get("content\_hash") or self.generate\_content\_hash( existing.get("title", ) if n ew\_hash == existing\_hash: r eturn True,"Duplicate Content Hash match"

\# 3. Fuzzy Text Similarity Check existing\_title = existing.get("title", similarity = fuzz.ratio(new\_title.lower(), existing\_title.lower()) if similarity \>= self.similarity\_threshold: r eturn True, f"Fuzzy similarity match ({similarity:.1f}%)"

r eturn False, None

"" )

"""

" .join(normalized\_text.split())

"" ).strip()""

"" )

"" ).strip()

"""" ), existing.get("description", )

"" )

# 4\. Unit Testing (pytest)

# Source Code: tests/test\_classifier.py

Python‎ import pytest from src.classifier import ProjectClassifier

def test\_project\_classifier(): classifier = ProjectClassifier()

\# T est 1: Web Project cat, conf, rel = classifier.classify( title="Need React Developer for Website",

description=" Looking to build a responsive website using React and Tailwind CSS",

"Tailwind"\] technologies=\["React",

)assert cat =="Web"

assert rel is True

assert conf \> 0.5

\# T est 2: App Project cat, conf, rel = classifier.classify( title="Flutter Mobile App for iOS and Android",

Build a cross- description=" platform mobile application using Flutter","Dart"\] technologies=\["Flutter",

)assert cat =="App"

assert rel is True

\# T est 3: Irrelevant Project cat, conf, rel = classifier.classify( title="Need Content Writer for Blog",

description=" Looking for someone to write articles about cooking","SEO"\] technologies=\["Writing",

)assert cat =="Other"

assert rel is False

# Source Code: tests/test\_deduplicator.py

Python‎ import pytest from src.deduplicator import ProjectDeduplicator

def test\_deduplicator\_matching(): deduplicator = ProjectDeduplicator(similarity\_threshold=85.0)

existing\_projects = \[ {"title":"Build a React Web Application",

"description":"We need a frontend developer using React and Tailwind CSS.",

"original\_url":"https://example.com/project/1" } \]

\# T est 1: Exact URL Match

n ew\_project\_url = {"title":"Completely Different Title",

"description":"Some random description.","original\_url":"https://example.com/project/1"

i}s\_dup, reason = deduplicator.is\_duplicate(new\_project\_url, existing\_projects)

assert is\_dup is True assert"URL"in r eason

\# T est 2: Content Hash Match

n ew\_project\_hash = {"title":"Build a React Web Application",

"description":"We need a frontend developer using React and Tailwind CSS.",

"original\_url":"https://example.com/project/2"

i}s\_dup, reason = deduplicator.is\_duplicate(new\_project\_hash,

existing\_projects) assert is\_dup is True assert"Hash"in r eason

\# T est 3: Fuzzy Match n ew\_project\_fuzzy = {"title":"Build a React Web Application!",

"description":"Different description text here.","original\_url":"https://example.com/project/3"

i}s\_dup, reason = deduplicator.is\_duplicate(new\_project\_fuzzy,

existing\_projects) assert is\_dup is True assert"Fuzzy"in r eason

\# T est 4: Unique Project n ew\_project\_unique = {"title":"Develop Mobile App with Flutter",

"description":"Need an Android and iOS developer.","original\_url":"https://example.com/project/4"

i}s\_dup, reason = deduplicator.is\_duplicate(new\_project\_unique,

existing\_projects) assert is\_dup is False assert reason is None

# 5\. Execution Commands & Results

## To run the unit tests within VS Code Terminal:

None‎

\# Activate Virtual Environment

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process .venv\\Scri pts\\Activate

\# Install Dependencies pip install rapidfuzz pytest

\# Run Unit Tests

python -m pytest tests/test\_classifier.py python -m pytest tests/test\_deduplicator.py

# Verified Test Results:

## \-​

## tests/test\_classifier.py: 1 passed in 0.11s

## \-​

## tests/test\_deduplicator.py: 1 passed in 0.53s

# 6\. Next Steps for Team Integration

1\.​Integrate ProjectClassifier inside scraper.py right after HTML parsing. 2.​Filter projects where is\_relevant == False.

## 3\.​Pass relevant records through ProjectDeduplicator.is\_duplicate() against

fetched Supabase records. 4.​Save unique projects into Supabase database via supabase\_mapper.py.