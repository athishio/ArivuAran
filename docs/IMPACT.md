# ARIVUARAN (அறிவுஅரண்) — Impact One-Pager
**Project:** ARIVUARAN (Voice-First Scam Helper for Tamil Citizens)  
**Track:** Digital India & Cybersecurity | **Theme:** Tech4Bharat | **Viksitthon 2026**  
**Team:** INEVITABLE (Athish M, Bavithiran V, Kamalesh T, Rohinth KV) — Nehru Institute of Technology, Coimbatore  

---

### 1. The Human & Financial Scale of the Problem

Cyber fraud in India has shifted from technical computer hacking to psychological social engineering targeting ordinary citizens, rural families, and senior citizens via SMS and phone calls.

* **National Scale:** Over **₹22,845 crore** was lost to cyber fraud across India in 2024 alone *(Official Lok Sabha reply, 22 Jul 2025)*.
* **National Recovery Effort:** While **₹8,189 crore** has been successfully saved across 23.61 lakh complaints via the 1930 / CFCFRMS helpline *(Rajya Sabha USQ 1349, 11 Feb 2026)*, recovery depends heavily on reporting within the **"Golden Hour"** (the first 2 to 4 hours before mule networks withdraw cash).
* **Tamil Nadu Vulnerability:** In Tamil Nadu alone, **1,85,584 cyber-fraud cases** were registered on the National Cybercrime Reporting Portal (NCRP), with an estimated **₹3,126 crore reported lost** *(Rajya Sabha USQ 1513, 12 Mar 2025)*.
* **The Last-Mile Gap:** The vast majority of victims in tier-2/tier-3 towns and rural panchayats cannot read English cybersecurity advisories, do not understand technical terms like "phishing" or "APKs", and panic when threatened with "power disconnection tonight" or "digital arrest".

---

### 2. Coimbatore Pilot Design (5 Blocks, ~500 Users)

Before scaling statewide, ARIVUARAN will be validated through a targeted 90-day pilot across 5 rural and semi-urban blocks in Coimbatore district, anchored by Nehru Institute of Technology:

| Block | Target Community | Outreach Partner | Primary Local Scam Pattern |
| :--- | :--- | :--- | :--- |
| **1. Kinathukadavu** | Farmers & Agri Traders | Agricultural Cooperative Societies & NSS | Fake PM-Kisan subsidy links, advance fertilizer token fees |
| **2. Madukkarai** | Factory Workers & Elders | Village Panchayats & Local SHG Groups | TNEB electricity bill disconnection threats |
| **3. Sulur** | Small Weaving & Textile Units | MSME Trade Associations & College NSS | Fake part-time rating tasks & pre-approved business loans |
| **4. Pollachi North** | Coconut Farmers & Elderly Residents | Senior Citizens Welfare Clubs & Post Offices | Fake bank KYC deactivation & Aadhaar card expiry calls |
| **5. Thondamuthur** | SHG Women & College Students | Mahalir Thittam (TNSRLM) Village Federations | Instant GPay refund / QR code collection scams |

#### Pilot Implementation Milestones
* **Weeks 1–4 (Community Onboarding):** Distribute single-page Tamil infographics during NSS digital literacy drives. Demonstrate forwarding messages to the ARIVUARAN Telegram bot.
* **Weeks 5–8 (Active Testing & Telemetry):** Monitor anonymous check frequency, common attack vectors, and false positive rates.
* **Weeks 9–12 (Impact Assessment):** Survey 50 active participants on whether voice explanations helped them avoid a scam or alert an elderly relative.

---

### 3. Key Impact Metrics (KPIs)

ARIVUARAN measures social and technical impact using four verifiable metrics:

1. **Pre-Incident Loss Prevention Rate:** Percentage of forwarded messages verified before the user clicks a link, transfers money, or shares an OTP (Target: > 85% of users check *before* acting).
2. **"Golden Hour" Reporting Acceleration:** Reduction in time between losing money and contacting **1930** or freezing bank accounts. By providing one-tap Tamil guidance and English dispute templates, ARIVUARAN cuts confusion time from hours to under 5 minutes.
3. **Linguistic Accessibility Index:** Percentage of users utilizing voice notes or audio playback rather than text-only replies (Target: > 60% in rural blocks).
4. **Community Scam Awareness:** Growth in district-level awareness through the anonymous choropleth map highlighting localized surges (e.g., sudden spikes in fake EB notices in Sulur).

---

### 4. Scale Roadmap: From 500 Users to Statewide Protection

```text
  Phase 1: Local Prototype        Phase 2: District Pilot        Phase 3: Statewide WhatsApp
   (Hackathon Prototype)           (Coimbatore 5 Blocks)            (Tamil Nadu Scale)
─────────────────────────────   ───────────────────────────   ───────────────────────────────
• Telegram Async Bot            • 500 active users            • Meta Cloud API WhatsApp Bot
• Local Whisper + Edge-TTS      • College NSS + SHG network   • Direct 1930 / I4C API linkage
• 60-sample benchmark verified  • District map live (Leaflet) • Local language packs (Tanglish)
• Sub-millisecond scoring       • Formal usability feedback   • Scaled on State Data Center / NIC
```

---

### 5. Ethics, Privacy & Consent Framework

Trust is the single most critical asset in scam prevention. ARIVUARAN is governed by strict ethical principles:

* **Zero-Knowledge Privacy Architecture:**  
  ARIVUARAN operates on zero user data retention. It **never** stores forwarded message texts, phone numbers, sender IDs, audio recordings, or bank details. Telegram Chat IDs are converted to one-way salted SHA-256 hashes for rate limiting and discarded.
* **Transparent Statistical Aggregation:**  
  District-level scam heatmaps only aggregate high-level category counters (e.g., "Electricity: 12 reports in Coimbatore"). Any district with fewer than 5 reports is masked to preserve anonymity.
* **No False Claims of Legal Filing:**  
  ARIVUARAN never claims to be a law enforcement agency or legal authority. It acts strictly as a trusted triage assistant, directing victims to official Government of India helplines (**1930**) and the National Cybercrime Reporting Portal (**cybercrime.gov.in**).
* **The "Never Safe" Rule:**  
  ARIVUARAN never tells a user *"This message is 100% safe"*. It reports: *"எச்சரிக்கை அறிகுறி எதுவும் இல்லை (No red flags found)"* along with the universal advisory: *"Never share your OTP or PIN with anyone."*
