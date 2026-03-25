# LinkedIn Email Integration Guide

## How to Use

### Step 1: Prepare LinkedIn Email CSV

When you scrape emails from LinkedIn, save them as a CSV file with this format:

```csv
company,email,person_name,location
GiftAbled,john.smith@giftabled.com,John Smith,Bangalore
Wobot Intelligence,sarah.khan@wobot.ai,Sarah Khan,Delhi
AryaXAI,raj.patel@aryaxai.com,Raj Patel,Mumbai
HCLTech,priya.sharma@hcltech.com,Priya Sharma,Lucknow
```

**Required columns**:
- `company` — Company name
- `email` — Email address

**Optional columns**:
- `person_name` — HR person's name (not required)
- `location` — City/region (helps with region detection)

### Step 2: Run the Importer

```bash
cd "E:\PROJECTS\Mission Job\job_pipeline"
python tools/linkedin_email_importer.py linkedin_emails.csv
```

**What happens**:
- ✅ Validates all emails
- ✅ Auto-detects region (Bangalore, Mumbai, Delhi-NCR, Lucknow)
- ✅ Deduplicates against existing Excel + sent log
- ✅ Merges into main contact list
- ✅ Adds to Excel with "LinkedIn" source tag
- ✅ Logs import history

### Step 3: Next Batch Automatically Uses New Contacts

The pipeline automatically:
1. Loads all contacts from Excel (both original HR list + new LinkedIn emails)
2. Detects their region
3. Uses region-specific pitch strategies
4. Continues sending at 200/day

**Example - What Changes**:

**Before** (Generic):
> "Hi there, I'm interested in opportunities at your company..."

**After** (Region-Aware):

**Bangalore Contact**:
> "I built a production 5-agent autonomous pipeline using LangChain and Claude API. Your work in agentic AI aligns perfectly with my expertise..."

**Delhi-NCR Contact**:
> "I deployed an 82% accurate YOLO system to Delhi Police. My computer vision background is ideal for industrial automation roles..."

### Step 4: Monitor Imports

Check import history anytime:
```bash
cat logs/linkedin_imports.json
```

Returns:
```json
{
  "2026-03-25T14:30:00": {
    "new_contacts": 45,
    "duplicates_skipped": 12,
    "regions": {
      "bangalore": 15,
      "delhi_ncr": 20,
      "mumbai": 8,
      "lucknow": 2
    }
  }
}
```

---

## Current Setup

**4 Automated Runs Daily**:
- 8:30 AM → 50 emails (200/day total)
- 12:30 PM → 50 emails
- 4:30 PM → 50 emails
- 8:30 PM → 50 emails

**Prioritization**:
1. LinkedIn-verified emails (higher quality, personalized)
2. Generic HR list (good coverage, broader reach)
3. Auto-skips: Already sent + bounced addresses

**Safe Limits**:
- 200/day sustainable (Gmail allows 500/day)
- 3-second delay between sends (looks human)
- DNS validation before sending
- Automatic bounce detection

---

## Workflow Example

1. **Monday 9 AM**: You extract 50 LinkedIn emails
2. **Monday 10 AM**: Run `python tools/linkedin_email_importer.py linkedin_monday.csv`
3. **Monday 12:30 PM**: Pipeline automatically uses new contacts + region-specific pitches
4. **Tuesday**: Check `logs/linkedin_imports.json` to see results

---

## Tips

- **Batch imports**: Collect 20-50 emails at a time before importing (more efficient)
- **Location matters**: If you can find location info, LinkedIn importer auto-detects region
- **Names are optional**: But helpful for personalization
- **No duplicates**: System automatically skips already-sent addresses
- **Track results**: Use `logs/sent_emails.json` to see all sent addresses

---

## Format Examples

### Minimal (just emails + companies):
```csv
company,email
GiftAbled,john@giftabled.com
Wobot,sarah@wobot.ai
```

### Full (with names + locations):
```csv
company,email,person_name,location
GiftAbled,john@giftabled.com,John Smith,Bangalore
Wobot,sarah@wobot.ai,Sarah Khan,Noida
AryaXAI,raj@aryaxai.com,Raj Patel,Mumbai
```

Both work fine! The system fills in missing data intelligently.

---

## Getting Started Right Now

When you have your first batch of LinkedIn emails:

1. Save as `linkedin_batch_1.csv`
2. Run: `python tools/linkedin_email_importer.py linkedin_batch_1.csv`
3. Watch it import + auto-tag regions
4. Next scheduled batch (8:30 AM / 12:30 PM / 4:30 PM / 8:30 PM) automatically sends to new contacts
