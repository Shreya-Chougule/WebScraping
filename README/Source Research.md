# ScrapeScout – Member 2 Task Assignment

**Assigned to:** Shree  
**Role:** Website Scraping and Data Extraction

## 1. Task Overview

Your responsibility is to develop a basic web scraper for ScrapeScout using Python.

The purpose of the scraper is to collect genuine client-posted projects and development opportunities from freelance platforms. The collected data will be processed and stored in our database so that it can later be displayed on the ScrapeScout dashboard.

I have already shortlisted five platforms that are relevant to our project:

1. Truelancer
2. PeoplePerHour
3. Guru
4. Freelancer.com
5. Malt

You do not need to conduct separate research on these platforms or find additional websites. You can choose **any one platform from this shortlist**, depending on which one is most convenient for you to access and technically implement a scraper for.

The objective is to select a suitable source and successfully extract project information from it.

## 2. What You Are Expected to Do

### Step 1: Select a Platform

- Go through the five shortlisted platforms.
- Check which platform is most convenient for you to work with technically.
- Consider how easily you can access project listings and their details.
- Select one platform from the list.
- Inform me which platform you have selected before proceeding.

**Note:** The selection is based on technical feasibility and implementation convenience. You are not expected to prepare a detailed research report comparing all five platforms.

### Step 2: Set Up the Scraper

Once the platform is selected:

- Use Python to develop the scraper.
- Set up the required libraries and environment.
- Identify the platform's project listing pages.
- Understand how project information is displayed on the website.
- Decide which extraction method is suitable.

You can use:

- `Requests` and `BeautifulSoup` for pages where the required information is available in the HTML.
- `Playwright` if the required content is loaded dynamically using JavaScript, provided the platform permits automated access.

### Step 3: Extract Project Information

The scraper should collect the following information wherever available:

| Field | Information to Extract |
|---|---|
| Project Title | Name or heading of the project |
| Description | Details and requirements mentioned by the client |
| Budget | Project budget or estimated price |
| Posted Date | Date when the project was posted |
| Deadline | Project submission deadline, if mentioned |
| Technologies | Technologies or skills required |
| Project Type | Web, App, Software or Both |
| Source Name | Name of the platform |
| Original URL | Direct link to the project |

**Important:** Extract only information that is actually available. Do not assume or create missing details. If a field is unavailable, leave it blank or store it as `null`.

### Step 4: Collect Multiple Project Listings

- Start by extracting a few project listings.
- Once the basic scraper works, extend it to collect multiple relevant projects.
- Extract project details from individual project pages wherever accessible.
- Include different types of development projects, such as:
  - Website development
  - Web application development
  - Mobile application development
  - Software development

The scraper should collect actual client requirements, not just website categories or general descriptions.

### Step 5: Clean and Organize the Data

After extracting the information:

- Remove unnecessary spaces and unwanted HTML elements.
- Keep the extracted descriptions readable.
- Maintain a consistent format for all records.
- Store the data in a structured format such as JSON or CSV.
- Ensure every project has its original source URL.

**Example of the expected output:**

```json
{
  "title": "E-commerce Website Development",
  "description": "Need a responsive online store with payment integration.",
  "budget": "₹50,000",
  "posted_date": "2026-10-25",
  "deadline": null,
  "technologies": ["React", "Node.js"],
  "project_type": "Web",
  "source_name": "Truelancer",
  "original_url": "https://example.com/project"
}
```

This is only an example of the expected structure.

### Step 6: Test and Validate the Scraper

- Run the scraper and check whether it collects project information correctly.
- Open the original project pages and compare the extracted details.
- Check whether the title, description, budget and other available fields are accurate.
- Identify and fix extraction errors.
- Make sure duplicate records are not unnecessarily collected.

If the platform requires login, blocks automated access, displays a CAPTCHA or restricts scraping, do not attempt to bypass those restrictions. Inform me so we can decide on an appropriate permitted approach.

### Step 7: Share the Final Output

Once the scraper is working, share the following:

1. Python scraper source code.
2. `requirements.txt` containing the required libraries.
3. JSON or CSV file containing the extracted projects.
4. A few sample project URLs for verification.
5. Basic instructions explaining how to run the scraper.
6. Any limitations or issues encountered during implementation.

## 3. Expected Outcome

By the end of this task, you should have:

- Selected one platform from the five shortlisted sources.
- Developed a working Python-based scraper.
- Extracted genuine client-posted project information.
- Collected the available project details in a structured format.
- Tested the extracted data against the original listings.
- Shared the scraper code and collected dataset with the team.

The main goal is to build a functional scraper that reliably extracts useful project information from at least one selected platform. We can consider integrating additional platforms after the first scraper is successfully completed.
