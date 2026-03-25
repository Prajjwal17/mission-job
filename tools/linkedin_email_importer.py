# tools/linkedin_email_importer.py
import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger(__name__)

# Region detection mapping
REGION_KEYWORDS = {
    "bangalore": ["bangalore", "bengaluru", "blr", "karnataka"],
    "mumbai": ["mumbai", "bombay", "maharashtra", "mh"],
    "delhi_ncr": ["delhi", "ncr", "noida", "gurgaon", "gurugram", "faridabad"],
    "lucknow": ["lucknow", "uttar pradesh", "up"]
}

def detect_region(company_name: str, location: str = "") -> str:
    """Detect region from company name or location."""
    search_text = f"{company_name} {location}".lower()
    
    for region, keywords in REGION_KEYWORDS.items():
        if any(kw in search_text for kw in keywords):
            return region
    
    return "unknown"

def validate_linkedin_email(row: Dict) -> Tuple[bool, str]:
    """
    Validate LinkedIn email entry.
    Expected format: {
        'company': 'Company Name',
        'email': 'name@company.com',
        'person_name': 'John Doe (optional)',
        'location': 'City (optional)'
    }
    """
    if not row.get('email') or '@' not in row['email']:
        return False, "Invalid email format"
    
    if not row.get('company'):
        return False, "Company name missing"
    
    return True, "Valid"

def import_linkedin_emails(csv_path: str, excel_path: str = "E:\23800+ HR Emails with Recruitment Agencies Contacts.xlsx") -> Dict:
    """
    Import LinkedIn-scraped emails into the main contact Excel file.
    
    Args:
        csv_path: Path to CSV with LinkedIn emails (format: company, email, person_name, location)
        excel_path: Path to main Excel file
    
    Returns:
        Dict with import statistics
    """
    
    stats = {
        "total_imported": 0,
        "duplicates_skipped": 0,
        "invalid_skipped": 0,
        "new_contacts": 0,
        "added_to_sent_log": False,
        "regions": {}
    }
    
    # Load LinkedIn CSV
    try:
        linkedin_df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(linkedin_df)} contacts from {csv_path}")
    except Exception as e:
        logger.error(f"Failed to load LinkedIn CSV: {e}")
        return stats
    
    # Load existing Excel
    try:
        excel_df = pd.read_excel(excel_path, sheet_name=0)
        logger.info(f"Loaded {len(excel_df)} existing contacts from Excel")
    except Exception as e:
        logger.error(f"Failed to load Excel: {e}")
        return stats
    
    # Load sent log
    sent_log_path = Path("logs/sent_emails.json")
    sent_emails = set()
    if sent_log_path.exists():
        with open(sent_log_path) as f:
            data = json.load(f)
            sent_emails = set(data.get("sent", []))
    
    # Process LinkedIn emails
    new_rows = []
    for idx, row in linkedin_df.iterrows():
        # Validate
        is_valid, msg = validate_linkedin_email(row)
        if not is_valid:
            logger.warning(f"Row {idx}: {msg}")
            stats["invalid_skipped"] += 1
            continue
        
        email = row['email'].strip().lower()
        company = row['company'].strip()
        person_name = row.get('person_name', '').strip()
        location = row.get('location', '').strip()
        
        # Check if already in sent log
        if email in sent_emails:
            logger.info(f"⏭️  Skipping {email} (already sent)")
            stats["duplicates_skipped"] += 1
            continue
        
        # Check if already in Excel
        if email in excel_df['HR Email'].values:
            logger.info(f"⏭️  Skipping {email} (already in Excel)")
            stats["duplicates_skipped"] += 1
            continue
        
        # Detect region
        region = detect_region(company, location)
        
        # Add to new rows
        new_rows.append({
            'Company Name': company,
            'HR Email': email,
            'HR Name': person_name,
            'Location': location,
            'Region': region,
            'Source': 'LinkedIn',
            'Verified': True,
            'Date Added': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        stats["new_contacts"] += 1
        stats["regions"][region] = stats["regions"].get(region, 0) + 1
        logger.info(f"✅ Added: {email} ({company}) - Region: {region}")
    
    if not new_rows:
        logger.info("No new contacts to add")
        return stats
    
    # Merge with existing
    new_df = pd.DataFrame(new_rows)
    merged_df = pd.concat([excel_df, new_df], ignore_index=True)
    
    # Deduplicate by email
    merged_df = merged_df.drop_duplicates(subset=['HR Email'], keep='first')
    
    # Save back to Excel
    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            merged_df.to_excel(writer, sheet_name=0, index=False)
        logger.info(f"✅ Saved {len(merged_df)} total contacts to Excel")
        stats["total_imported"] = len(new_rows)
    except Exception as e:
        logger.error(f"Failed to save Excel: {e}")
        return stats
    
    # Log import
    import_log_path = Path("logs/linkedin_imports.json")
    import_history = {}
    if import_log_path.exists():
        with open(import_log_path) as f:
            import_history = json.load(f)
    
    import_history[pd.Timestamp.now().isoformat()] = {
        "new_contacts": stats["new_contacts"],
        "duplicates_skipped": stats["duplicates_skipped"],
        "regions": stats["regions"]
    }
    
    with open(import_log_path, 'w') as f:
        json.dump(import_history, f, indent=2)
    
    logger.info(f"""
============================================================
LINKEDIN EMAIL IMPORT COMPLETE
  New contacts added: {stats['new_contacts']}
  Duplicates skipped: {stats['duplicates_skipped']}
  Invalid skipped: {stats['invalid_skipped']}
  By region: {stats['regions']}
  Total contacts now: {len(merged_df)}
============================================================
""")
    
    return stats

# CLI usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python linkedin_email_importer.py <csv_path> [excel_path]")
        print("Example: python linkedin_email_importer.py linkedin_emails.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    excel_file = sys.argv[2] if len(sys.argv) > 2 else "E:\23800+ HR Emails with Recruitment Agencies Contacts.xlsx"
    
    result = import_linkedin_emails(csv_file, excel_file)
    print(json.dumps(result, indent=2))
