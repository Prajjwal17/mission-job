# tools/strategic_filter.py
# ============================================================
# STRATEGIC COMPANY FILTERING
# Filters contacts by skill-matched companies from strategic analysis
# ============================================================

import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class StrategicFilter:
    """
    Loads and filters contacts based on strategic company analysis.
    Uses: strategic_target_companies_clean.csv
    """

    def __init__(self, strategic_csv_path: str = "strategic_target_companies_clean.csv"):
        """
        Load strategic companies from CSV.

        Expected columns: Company, Skill Area, Skill Match Score, Available Contacts
        """
        self.strategic_companies = {}  # company -> {skill_area, score, contacts}
        self.skill_areas = {}           # skill_area -> [companies]

        if not Path(strategic_csv_path).exists():
            logger.warning(f"Strategic CSV not found at {strategic_csv_path}. Using all contacts.")
            self.enabled = False
            return

        try:
            with open(strategic_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    company = row['Company'].strip()
                    skill_area = row['Skill Area'].strip()

                    self.strategic_companies[company.lower()] = {
                        'company': company,
                        'skill_area': skill_area,
                        'score': int(row['Skill Match Score']),
                        'contacts': int(row['Available Contacts'])
                    }

                    if skill_area not in self.skill_areas:
                        self.skill_areas[skill_area] = []
                    self.skill_areas[skill_area].append(company)

            logger.info(f"[+] Loaded {len(self.strategic_companies)} strategic companies")
            for skill, companies in self.skill_areas.items():
                logger.info(f"    {skill}: {len(companies)} companies")

            self.enabled = True

        except Exception as e:
            logger.error(f"Failed to load strategic CSV: {e}")
            self.enabled = False

    def extract_company(self, email: str) -> Optional[str]:
        """
        Extract company name from email domain.
        Examples: john@microsoft.com -> microsoft
                  hr@flipkart-careers.com -> flipkart
        """
        if not email or '@' not in email:
            return None

        domain = email.split('@')[1].lower()
        company_part = domain.split('.')[0]

        # Clean common patterns
        company_part = company_part.replace('-careers', '').replace('_careers', '')

        return company_part if company_part else None

    def find_strategic_match(self, email: str, company_name: str = None) -> Optional[Dict]:
        """
        Find if contact's company is in strategic list.

        Args:
            email: HR email address
            company_name: Company name (if available)

        Returns:
            Dict with {company, skill_area, score, contacts} or None
        """
        if not self.enabled:
            return None

        # Try direct company name match first
        if company_name:
            company_lower = company_name.lower().strip()
            if company_lower in self.strategic_companies:
                return self.strategic_companies[company_lower]

            # Fuzzy match (contains check)
            for strat_company, data in self.strategic_companies.items():
                if strat_company in company_lower or company_lower in strat_company:
                    return data

        # Try email domain extraction
        extracted = self.extract_company(email)
        if extracted:
            # Direct match
            for strat_company, data in self.strategic_companies.items():
                if extracted in strat_company.lower():
                    return data

        return None

    def filter_contacts(self, contacts: List[Dict],
                       strategy: str = "strategic_only") -> tuple[List[Dict], Dict]:
        """
        Filter contacts based on strategy.

        Args:
            contacts: List of contact dicts
            strategy:
                - "strategic_only": Only return strategic companies
                - "strategic_first": Return strategic first, then others
                - "all": Return all (no filtering)

        Returns:
            (filtered_contacts, statistics)
        """
        if not self.enabled or strategy == "all":
            return contacts, {"total": len(contacts), "filtered": len(contacts)}

        strategic_contacts = []
        non_strategic_contacts = []
        stats = {
            "total": len(contacts),
            "strategic": 0,
            "non_strategic": 0,
            "by_skill": {}
        }

        for contact in contacts:
            company = contact.get('company', '')
            email = contact.get('hr_email', '')

            match = self.find_strategic_match(email, company)

            if match:
                contact['skill_area'] = match['skill_area']
                contact['skill_score'] = match['score']
                strategic_contacts.append(contact)
                stats["strategic"] += 1

                skill = match['skill_area']
                if skill not in stats["by_skill"]:
                    stats["by_skill"][skill] = 0
                stats["by_skill"][skill] += 1
            else:
                non_strategic_contacts.append(contact)
                stats["non_strategic"] += 1

        # Return based on strategy
        if strategy == "strategic_only":
            result = strategic_contacts
        elif strategy == "strategic_first":
            result = strategic_contacts + non_strategic_contacts
        else:
            result = contacts

        stats["filtered"] = len(result)

        logger.info(f"[+] Filtering result: {stats['strategic']} strategic + {stats['non_strategic']} non-strategic")
        if stats["by_skill"]:
            for skill, count in stats["by_skill"].items():
                logger.info(f"    {skill}: {count}")

        return result, stats

    def get_skill_area(self, email: str, company_name: str = None) -> Optional[str]:
        """Get the skill area for a contact."""
        match = self.find_strategic_match(email, company_name)
        return match['skill_area'] if match else None

    def export_statistics(self, contacts: List[Dict], output_path: str = "logs/strategic_stats.json"):
        """
        Export statistics about which companies/skills are being contacted.
        """
        stats = {
            "total_contacts": len(contacts),
            "by_company": {},
            "by_skill": {},
            "top_companies": []
        }

        for contact in contacts:
            company = contact.get('company', 'Unknown')
            skill = contact.get('skill_area', 'No Skill Match')

            if company not in stats["by_company"]:
                stats["by_company"][company] = 0
            stats["by_company"][company] += 1

            if skill not in stats["by_skill"]:
                stats["by_skill"][skill] = 0
            stats["by_skill"][skill] += 1

        # Top companies by contact count
        stats["top_companies"] = sorted(
            stats["by_company"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        logger.info(f"[+] Exported strategic statistics to {output_path}")
        return stats
