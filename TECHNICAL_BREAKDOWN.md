# AfixTech Business Lead Finder: Technical Breakdown & Architecture Specification

---

## Executive Summary

The **AfixTech Business Lead Finder** is a specialized lead generation, website verification, lead scoring, and outreach management system designed specifically for **AfixTech** to identify high-value B2B prospects (local businesses without websites or with substandard web presence) and convert them into website development clients.

This document provides a comprehensive technical breakdown covering data collection methodologies, URL parsing, email discovery strategies, classification and secondary verification workflows, lead scoring logic, anti-bot mitigation, compliance standards, database architecture (Supabase PostgreSQL), web dashboard setup (Flask on Vercel), and cold outreach automation.

---

## 1. Approaches & Tools Comparison

To extract local business listings from Google Maps, three primary methodologies exist. Below is a comparative evaluation across data completeness, cost, rate limits, anti-bot resistance, legal risk, and maintenance overhead.

| Criteria | Google Places API (Text Search + Place Details) | Headless Browser Scraping (Playwright / Puppeteer) | Third-Party APIs (Outscraper / SerpAPI) |
| :--- | :--- | :--- | :--- |
| **Official Documentation** | [Google Places API Docs](https://developers.google.com/maps/documentation/places/web-service) | [Playwright Documentation](https://playwright.dev/python/) | [SerpAPI Google Maps Docs](https://serpapi.com/google-maps-api) / [Outscraper Docs](https://outscraper.com/docs/) |
| **Data Extraction Reliability** | 100% structured JSON response, official SLA, no risk of page structure breaks. | Moderate; Google Maps DOM changes frequently requiring maintenance. | High; Managed wrapper around Google Maps SERP parsing. |
| **Fields Returned** | Name, Address, Phone, Website URL, Place ID, Map URL, Category, Ratings, Reviews, Business Hours. *(Note: Email NOT available)* | Name, Address, Phone, Website URL, Place ID, Map URL, Category, Ratings, Reviews. *(Note: Email NOT available)* | Name, Address, Phone, Website URL, Place ID, Map URL, Category, Ratings, Reviews. *(Note: Email NOT available)* |
| **Email Extraction** | ❌ No native email fields in Google Places API. | ❌ No native email on Google Maps SERP. | ⚠️ Some third-party APIs offer optional web-crawling add-ons for email enrichment. |
| **Cost Structure** | $17 per 1,000 Text Search requests; $17 per 1,000 Place Details requests. $200 free monthly credit (~10,000 requests/mo). | Low direct cost (infrastructure only); high compute cost for headless browsers (RAM/CPU) + proxy costs. | ~$2 to $3 per 1,000 listings (Outscraper/SerpAPI tier dependent). |
| **Rate Limits** | 100 QPS (Queries Per Second) default limit; scalable upon request. | Subject to Google's IP blocks, CAPTCHAs, and rate limits (~10-20 pages/min per IP). | Managed rate limits handled transparently by API provider. |
| **Anti-Bot Resistance** | N/A (Official API key authentication). | Requires proxy rotation (residential), stealth browser plugins, fingerprint randomization. | Managed entirely by third-party provider. |
| **Legal & Compliance** | Fully compliant with Google Terms of Service; no scraping terms violated. | Violates Google TOS Sec 3.2.3 (No Automated Access/Scraping). Risk of IP ban. | Terms governed by API service provider. |
| **Query Flexibility** | Accepts search terms (`restaurants in Abeokuta`) or lat/lng location biases. | Can accept raw Google Maps URLs or direct search phrases. | Accepts search queries or Google Maps search URLs directly. |

---

## 2. Google Maps Available Fields & Email Discovery Reality

### 2.1 Native Google Maps Data Fields
Google Maps listing objects contain the following public business attributes:
* **Business Name**: Official registered or display name.
* **Category**: Primary and secondary business categories (e.g., "Car Repair Workshop", "Italian Restaurant").
* **Formatted Address & Coordinates**: Full physical address, street, city, state, postal code, latitude/longitude.
* **Phone Number**: Primary international or local phone number.
* **Website URL**: Listed domain destination (if claimed/provided by business owner).
* **Google Maps URL / Place ID**: Permanent URL link (`https://maps.google.com/?cid=...`) and unique alphanumeric Place ID.
* **Rating & Review Count**: Average star rating (1.0 to 5.0) and total user reviews.
* **Operating Hours & Business Status**: Operational state (`OPERATIONAL`, `CLOSED_TEMPORARILY`, `CLOSED_PERMANENTLY`).

### 2.2 Critical Distinction: Email Availability
> ⚠️ **CRITICAL TECHNICAL NOTE**: Google Maps **DOES NOT** store or expose business email addresses in its directory or public API responses. Any system claiming to pull emails directly from Google Maps is executing secondary crawling or third-party enrichment under the hood.

### 2.3 Email Discovery & Enrichment Workflow
To discover business email addresses for AfixTech lead generation, the system implements a multi-tier enrichment pipeline:
1. **Listed Website Crawling**: For listings that *do* have a website URL listed on Google Maps, an asynchronous HTTP client (or Playwright) crawls public pages (`/`, `/contact`, `/about`, `/imprint`, `/privacy`) to parse regex patterns (`mailto:` links and email regex matching `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`).
2. **Social Media & Directory Web Search**: For businesses without a listed website, automated Google search queries (e.g., `"Business Name" "Ikeja" email OR "@gmail.com" OR "@yahoo.com"`) search Facebook Pages, Instagram bios, LinkedIn, and local business directories (e.g., VConnect, BusinessList Nigeria).
3. **Domain WHOIS Lookup**: Query WHOIS registry records for domain owner contacts (where GDPR privacy masking is not applied).
4. **Email Verification**: Validate extracted emails using DNS MX record checks, SMTP handshake tests, and syntax validation to filter out spam traps and disposable emails.

---

## 3. Website Detection & Secondary Verification Framework

### 3.1 Website Status Classification Engine
Businesses are categorized into four distinct structural states:

```
                          [ Business Listing Discovered ]
                                        │
                       ┌────────────────┴────────────────┐
                       ▼                                 ▼
             [ Google Maps Has Website ]       [ Google Maps No Website ]
                       │                                 │
           ┌───────────┴───────────┐           ┌─────────┴─────────┐
           ▼                       ▼           ▼                   ▼
    [ Website Accessible ]  [ Website Dead/Error ] [ Verified No Web ] [ Web Found Else ]
           │                       │                   │                   │
  (Website Listed)        (Website Unavailable) (No Website Listed) (Requires Verif.)
```

1. **`Website Listed`** (`has_website=true`): Google Maps lists a URL, and HTTP GET check returns status `200 OK` with valid HTML content.
2. **`No Website Listed`** (`has_website=false`): Google Maps lacks a URL, and secondary verification confirms no active independent domain exists.
3. **`Website Requires Verification`** (`has_website=false` on Maps, but pending verification): Google Maps lacks a URL, but secondary search reveals an unverified domain or active Facebook/Instagram page acting as their de facto web presence.
4. **`Website Unavailable or Inaccessible`** (`has_website=true` on Maps, but site is dead): Google Maps lists a URL, but the link returns HTTP errors (`404 Not Found`, `500 Server Error`, `502 Bad Gateway`, `DNS_PROBE_FINISHED_NXDOMAIN`, SSL certification errors, or connection timeouts). *These are high-priority candidates for AfixTech website rebuilds/repairs.*

### 3.2 Secondary Verification Logic for "No Website" Listings
To avoid false positives (assuming a business has no website when Google Maps is merely outdated), the secondary verification algorithm performs:
* **Custom Search API / Web Search Query**: `"Business Name" + "Location" + "official site" OR "website"`
* **Social Presence Check**: Scrapes public Facebook/Instagram/TikTok profiles for links.
* **Domain Search**: Checks domain availability for `businessname.com` or `businessname.ng` via DNS lookup.
* **Confidence Rating**: Assigns a Verification Confidence Score (0% - 100%) and updates `Website Verification Status` with explicit proof notes (e.g., "Verified No Website via Web Search & DNS").

---

## 4. Rate Limits, Cost Analysis, and Anti-Bot Mitigation

### 4.1 Cost & Scale Comparison Matrix

| Option | Scale Capability | Monthly Cost (10,000 Leads) | Maintenance Overhead | Anti-Bot Management Needed? |
| :--- | :--- | :--- | :--- | :--- |
| **Google Places API** | High (Unlimited scaling) | ~$170 - $340 | Low | No (API Key Auth) |
| **Outscraper API** | High | ~$30 - $50 | Low | No (Handled by Outscraper) |
| **SerpAPI** | Medium | ~$50 - $100 | Low | No (Handled by SerpAPI) |
| **Self-Hosted Playwright** | Low - Medium | ~$10 - $30 (Proxy cost) | High (DOM breaks, CAPTCHA) | Yes (Residential Proxies + Stealth) |

### 4.2 Anti-Bot Handling Strategies (For Web Scraping & Crawling)
When executing secondary verification or crawling business websites for emails:
1. **Residential Proxy Rotation**: Rotate residential IP addresses per request batch to prevent IP bans.
2. **Stealth Headless Browsers**: Utilize `playwright-stealth` or `puppeteer-extra-plugin-stealth` to bypass WebGL fingerprinting, Chrome driver flags (`navigator.webdriver`), and browser automation signatures.
3. **Request Rate Throttling**: Implement exponential backoff and randomized delays (e.g., 2.5s to 6.0s jitter between page visits).
4. **HTTP Header Spoofing**: Rotate realistic User-Agent strings, Accept-Language headers (`en-US,en;q=0.9`), SEC-CH-UA browser headers, and referrer headers (`https://www.google.com/`).
5. **CAPTCHA Avoidance**: Handle 429 / 403 response codes gracefully with queue re-try policies and CAPTCHA solving services (e.g., 2Captcha) if necessary.

---

## 5. System Architecture: 15-Step Workflow

Below is the exhaustive 15-step technical specification mapping user workflows to data processing pipelines, database schemas, and Flask/Supabase components.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                SYSTEM ARCHITECTURE WORKFLOW                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [Step 1: Input] -> [Step 2: Parse Query] -> [Step 3: Fetch Listings (Google Places)]   │
│                                                                  │                     │
│ [Step 6: Verify No Web] <- [Step 5: Classify Web] <- [Step 4: Deep Web Crawl Email]   │
│         │                                                                              │
│         ▼                                                                              │
│ [Step 7: Lead Scoring] -> [Step 8: Clean/Deduplicate] -> [Step 9: Export CSV / DB]    │
│                                                                  │                     │
│ [Step 12: Manual Send] <- [Step 11: Draft Template] <- [Step 10: Qualification UI]    │
│         │                                                                              │
│         ▼                                                                              │
│ [Step 13: Track Pipeline] -> [Step 14: Flask Dashboard] -> [Step 15: System Analytics] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### STEP 1: USER INPUT
* **Functionality**: Multi-modal user interface accepting either a raw Google Maps URL or direct text query phrases.
* **Input Examples**:
  * URL: `https://www.google.com/maps/search/restaurants+in+Lagos/@6.5243793,3.3792057,12z`
  * URL: `https://maps.app.goo.gl/xY12z345...`
  * Phrase: `"car repair workshops in Ikeja, Lagos"`
  * Phrase: `"hotels in Abeokuta"`

### STEP 2: EXTRACT THE SEARCH QUERY
* **URL Parsing Logic**:
  * Unshorten `maps.app.goo.gl` links via HTTP HEAD request location headers.
  * Extract search parameters using regular expressions / URL parameter parsing:
    * Regex for `/maps/search/(.*?)/`: Extracts `restaurants in Lagos`.
    * Query parameter extraction (`?q=...`): Decodes URL-encoded parameters (`q=car+repair+workshops+in+Ikeja`).
* **Validation**: Display extracted query to user for explicit confirmation before API invocation.

### STEP 3: RETRIEVE BUSINESS LISTINGS
* **Execution**: Query Google Places API (`Text Search` v1 / Place Search) or secondary fallback scraper using the validated query.
* **Pagination & Max Limit**: Implement loop pagination handling `next_page_token` up to the user-specified limit (e.g., 20, 50, 100, 500 listings).
* **Extracted Primary Fields**: Business Name, Category, Address, Phone Number, Website URL, Google Maps URL, Place ID.

### STEP 4: CHECK BUSINESS WEBSITES
* **Execution**: For records containing a `website_url`, asynchronously fetch the site's public HTML structure (`/`, `/contact`, `/about`).
* **Safe Crawling Policy**:
  * Timeout capped at 8 seconds per site.
  * Respect `robots.txt` disallow rules where applicable.
  * Execute regex parsing for `mailto:` and plaintext email signatures.
  * Avoid forms, authentication pages, or script executions that bypass site terms.

### STEP 5: CLASSIFY BUSINESSES
* **Classification Rules**:
  * `Website listed`: URL present and HTTP response status `2xx`.
  * `No website listed`: No URL present in Google Places API result.
  * `Website requires verification`: Unlisted on Maps, but web search finds potential matching domains.
  * `Website unavailable or inaccessible`: Listed URL returns HTTP `4xx`, `5xx`, DNS failure, or SSL error.

### STEP 6: VERIFY WEBSITE EXISTENCE
* **Execution**: For all `No website listed` prospects:
  * Query Google Custom Search API for `"{Business Name}" "{City}"`.
  * Verify domain ownership match (check business name similarity vs domain title/meta description).
  * Record verification status (`Verified No Website`, `Website Found Elsewhere`, `Uncertain`).
  * Record proof notes (e.g., "Google Search returned 0 matching business domains. Confirmed no website.").

### STEP 7: SCORE AND PRIORITISE LEADS
* **Lead Priority Scoring Algorithm (0 - 100 Points)**:
  * **Website Need (Max 40 pts)**:
    * No website listed & verified absent = `+40 pts`
    * Website broken/unavailable = `+35 pts`
    * Website exists = `+0 pts`
  * **Contact Quality (Max 30 pts)**:
    * Public Email available = `+15 pts`
    * Phone Number available = `+15 pts`
  * **Business Readiness & Activity (Max 20 pts)**:
    * High review count (>10 reviews) = `+10 pts` (Indicates active business with budget)
    * High rating (>4.0 stars) = `+10 pts`
  * **AfixTech Service Match (Max 10 pts)**:
    * High-value service categories (Restaurants, Repair Workshops, Hotels, Real Estate, Law Firms) = `+10 pts`
* **Priority Tiers**:
  * **High Priority**: Score ≥ 70 (Prime prospect: Active business, no website/broken website, phone & email available).
  * **Medium Priority**: Score 40 – 69 (No website, phone available, missing email).
  * **Low Priority**: Score < 40 (Existing functional website or low activity/inactive).

### STEP 8: CLEAN AND ORGANISE THE DATA
* **Deduplication**: Deduplicate by `place_id`, normalized phone number (E.164 format: `+234...`), or exact Business Name + Address match.
* **Standardization**: Clean phone numbers to international/national formatting; trim and format URLs (`https://`).
* **Null Handling**: Clear visual markers for missing data (`N/A` or empty string in DB).

### STEP 9: EXPORT THE RESULTS
* **CSV Export**: Generate downloadable UTF-8 CSV named `afixtech_business_leads.csv`.
* **Exact 15-Column Schema Specification**:
  1. `business_name` (Text)
  2. `business_category` (Text)
  3. `business_address` (Text)
  4. `phone_number` (Text)
  5. `email_address` (Text)
  6. `website_url` (Text)
  7. `website_status` (`Website listed` | `No website listed` | `Website requires verification` | `Website unavailable or inaccessible`)
  8. `website_verification_status` (`Verified No Website` | `Website Found Elsewhere` | `Uncertain`)
  9. `google_maps_url` (Text)
  10. `lead_priority_score` (Integer 0-100)
  11. `lead_priority_category` (`High` | `Medium` | `Low`)
  12. `email_research_status` (`Found` | `Not Found` | `Pending` | `Invalid`)
  13. `research_notes` (Text summary of verification/crawling findings)
  14. `outreach_status` (`New` | `Draft Prepared` | `Contacted` | `Replied` | `Interested` | `Not Interested`)
  15. `follow_up_date` (Date ISO `YYYY-MM-DD` or blank)

### STEP 10: REVIEW AND QUALIFY LEADS
* **User Interface**: Interactive Flask table enabling search, filtering by Priority Tier or Category, manual editing of lead details, and explicit qualification checkboxes before outreach generation.

### STEP 11: GENERATE PERSONALISED OUTREACH EMAILS
* **Category-Aware Email Engine**: Dynamic template generation targeting specific industry pain points:
  * **Restaurants / Hospitality**: Focus on online menu displays, WhatsApp table reservations, food delivery integrations, and customer review showcases.
  * **Car Repair Workshops / Service Centers**: Focus on online service catalog, instant quote request forms, location mapping, and direct WhatsApp booking buttons.
  * **Hotels / Guest Houses**: Focus on direct room booking engine (avoiding OTA commissions), photo galleries, and customer inquiry forms.
* **Template Structure**:
  1. *Subject line*: Clear, non-spammy value proposition tailored to business name.
  2. *Introduction*: Personal greeting referencing their specific business in their local area (e.g., Ikeja / Lagos).
  3. *Observation*: Non-judgmental observation (e.g., "I noticed your workshop on Google Maps has excellent reviews, but customers can't book services or view your catalog online.").
  4. *Solution & Value*: Brief summary of how an AfixTech custom site drives revenue and client trust.
  5. *Call to Action*: Low-friction invitation (e.g., "Reply to this email or click here for a 5-minute WhatsApp call").

### STEP 12: CONTACT BUSINESSES
* **Manual Review & Send**: One-click email dispatch from Flask dashboard (via SMTP/SendGrid/Resend API) after user approval.
* **Safeguards**: Daily sending caps (e.g., max 50 cold emails/day per domain to preserve deliverability), unsubscribed domain blocklist checks.

### STEP 13: TRACK OUTREACH AND FOLLOW UPS
* **Pipeline Management**: Visual kanban / status transition pipeline:
  `Prepared` ➔ `Sent` ➔ `Replied` ➔ `Interested` ➔ `Follow Up Scheduled` ➔ `Meeting Arranged` ➔ `Proposal Submitted` ➔ `Project Won` / `Project Lost`
* **Automated Follow-Up Reminders**: Visual indicators on Flask dashboard when `follow_up_date` is due.

### STEP 14: BUILD A LEAD MANAGEMENT DASHBOARD
* **Tech Stack**:
  * **Backend Framework**: Python Flask.
  * **Database**: Supabase PostgreSQL (managed PostgreSQL database with REST/Python client).
  * **Deployment Platform**: Vercel (using Vercel WSGI / Serverless Python functions or render/Railway app engine).
  * **Frontend**: HTML5, Tailwind CSS, JavaScript (Alpine.js / DataTables).
* **Dashboard Features**:
  * Real-time metrics counters (Total Discovered, Businesses Without Website, Verified Leads, Emails Discovered, Outreach Sent, Conversion Rate).
  * Global search, multi-column sorting, priority filtering.
  * CSV/Excel export triggers.

### STEP 15: IMPROVE THE SYSTEM OVER TIME
* **Future Expansion Roadmap**:
  * Automated email verification service integration (NeverBounce / ZeroBounce API).
  * Webhook integrations for instant WhatsApp notifications.
  * Machine-learning lead scoring adjustments based on historical project conversion rates.
  * Multi-template A/B testing for email response rate optimization.

---

## 6. Cold Outreach Legal Compliance (CAN-SPAM, GDPR, NDPR)

Because outreach will target business entities (primarily in Nigeria and internationally), the system adheres strictly to statutory digital marketing regulations:

### 6.1 Compliance Framework
* **CAN-SPAM Act (USA & International Standards)**:
  * Non-deceptive headers and subject lines.
  * Clear identification that the message is an introductory business proposal.
  * Physical mailing address / contact information included in email footer.
  * Clear, simple opt-out mechanism (e.g., "Reply 'STOP' or click Unsubscribe to opt out").
  * Immediate honoring of unsubscribe requests within 10 business days (enforced automatically in database blocklist).
* **GDPR (EU) & NDPR (Nigeria Data Protection Regulation)**:
  * B2B Cold Outreach is permitted under **Legitimate Interest** (GDPR Recital 47 & NDPR guidance) provided the communication is strictly relevant to the business recipient's professional role.
  * Only publicly available corporate contact information (business email, corporate phone) is processed. No private personal data is collected.
  * Data minimisation: Store only fields essential for lead evaluation and outreach tracking.

---

## 7. Recommended Technology Stack

For maximum performance, maintainability, low operating cost, and zero server maintenance overhead, the following production stack is recommended:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           RECOMMENDED TECH STACK                        │
├─────────────────────────────────────────────────────────────────────────┤
│ • Web Framework:   Flask (Python 3.11+)                                 │
│ • Database:        Supabase PostgreSQL (Free Tier: 500MB DB, Auth, API)  │
│ • Deployment:      Vercel / Render                                      │
│ • Data Retrieval:  Google Places API (Official) + Web Crawler          │
│ • Scraping/Crawl:  Playwright Python Async                              │
│ • Frontend UI:     Tailwind CSS + Alpine.js + DataTables                 │
│ • Email Service:   Resend API / SendGrid / SMTP                         │
│ • Data Export:     Python Pandas / Native CSV                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Summary & Next Steps

This technical breakdown provides the complete architectural roadmap for the **AfixTech Business Lead Finder**. It resolves all technical ambiguities surrounding Google Maps URL parsing, email discovery constraints, website verification logic, lead scoring, compliance, and cloud deployment.

Once this technical breakdown document is reviewed and approved, implementation can proceed seamlessly across the 15 system development steps.
