"""
SEC EDGAR filing source.

Tracks material events for AI sector companies via SEC filings.
Focus on 8-K (material events), 10-Q/K (quarterly/annual reports).

Why this matters: Companies MUST disclose material events within 4 days.
This catches major news before it's widely reported.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class SECEdgarSource:
    """
    Fetches SEC filings for AI sector companies.

    Material events that trigger 8-K filings:
    - Major contracts
    - Executive changes
    - Acquisitions
    - Material agreements
    - Financial results
    """

    # Key AI sector companies
    COMPANIES = {
        'NVIDIA': '0001045810',
        'Microsoft': '0000789019',
        'Alphabet': '0001652044',  # Google
        'Meta': '0001326801',      # Facebook
        'AMD': '0000002488',
        'Intel': '0000050863',
        'Amazon': '0001018724',
        'Tesla': '0001318605',     # AI/robotics
        'Oracle': '0001341439',    # Cloud AI
        'Broadcom': '0001730168',  # AI chips
    }

    # Filing types to track
    FILING_TYPES = {
        '8-K': 'Material events (most important)',
        '10-Q': 'Quarterly report',
        '10-K': 'Annual report',
        'S-1': 'IPO registration',
        'SC 13D': 'Major ownership change (>5%)',
    }

    def __init__(self):
        """Initialize SEC EDGAR source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse mat.edwards@example.com',  # SEC requires user agent
            'Accept-Encoding': 'gzip, deflate',
        })

    def fetch_recent_filings(self, company: str, cik: str,
                            filing_type: str = '8-K',
                            days_back: int = 7) -> List[dict]:
        """
        Fetch recent filings for a company.

        Args:
            company: Company name
            cik: SEC CIK number
            filing_type: Type of filing (8-K, 10-Q, etc.)
            days_back: How many days to look back

        Returns:
            List of filing dictionaries
        """
        # SEC RSS feed URL
        url = f"https://www.sec.gov/cgi-bin/browse-edgar"

        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': '',  # End date (empty = today)
            'owner': 'exclude',
            'count': 20,  # Number of filings to fetch
            'output': 'atom',  # RSS/Atom format
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            # Parse Atom/RSS feed
            filings = self._parse_atom_feed(response.text, company, days_back)

            return filings

        except Exception as e:
            print(f"Error fetching {company} filings: {e}")
            return []

    def _parse_atom_feed(self, xml_content: str, company: str, days_back: int) -> List[dict]:
        """Parse SEC Atom feed"""
        try:
            root = ET.fromstring(xml_content)

            # Namespace handling
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            filings = []
            cutoff = datetime.utcnow() - timedelta(days=days_back)

            for entry in root.findall('atom:entry', ns):
                # Extract filing info
                title_elem = entry.find('atom:title', ns)
                link_elem = entry.find('atom:link', ns)
                updated_elem = entry.find('atom:updated', ns)
                summary_elem = entry.find('atom:summary', ns)

                if not all([title_elem, link_elem, updated_elem]):
                    continue

                title = title_elem.text
                link = link_elem.get('href')
                updated_str = updated_elem.text
                summary = summary_elem.text if summary_elem is not None else ""

                # Parse date
                try:
                    # Format: 2025-11-11T16:30:00-05:00
                    updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                except:
                    updated = datetime.utcnow()

                # Filter by date
                if updated < cutoff:
                    continue

                filings.append({
                    'company': company,
                    'title': title,
                    'link': link,
                    'updated': updated,
                    'summary': summary,
                })

            return filings

        except Exception as e:
            print(f"Error parsing Atom feed: {e}")
            return []

    def classify_filing_significance(self, title: str, summary: str) -> EventType:
        """Classify filing type based on content"""
        text = (title + " " + summary).lower()

        if 'acquisition' in text or 'merger' in text or 'agreement' in text:
            return EventType.PARTNERSHIP
        elif 'result' in text or 'earnings' in text or 'financial' in text:
            return EventType.NEWS
        elif any(word in text for word in ['appoint', 'resign', 'executive', 'officer']):
            return EventType.NEWS
        else:
            return EventType.NEWS

    def filing_to_event(self, filing: dict, filing_type: str) -> Event:
        """Convert SEC filing to Event object"""

        event = Event(
            source=EventSource.SEC_EDGAR,
            source_id=filing['link'].split('/')[-1],  # Filing ID from URL
            source_url=filing['link'],
            title=f"{filing['company']} files {filing_type}: {filing['title']}",
            summary=filing.get('summary', ''),
            event_type=self.classify_filing_significance(filing['title'], filing.get('summary', '')),
            companies=[filing['company']],
            published_at=filing['updated'],
        )

        return event

    def fetch_all_companies(self, filing_type: str = '8-K', days_back: int = 7) -> List[Event]:
        """
        Fetch filings for all tracked companies.

        Args:
            filing_type: Type of filing to track
            days_back: Days to look back

        Returns:
            List of Event objects
        """
        print(f"Fetching {filing_type} filings for AI sector companies (last {days_back} days)...")

        all_events = []

        for company, cik in self.COMPANIES.items():
            print(f"  Checking {company}...", end=' ')

            filings = self.fetch_recent_filings(company, cik, filing_type, days_back)

            if filings:
                print(f"✓ {len(filings)} filing(s)")
                for filing in filings:
                    event = self.filing_to_event(filing, filing_type)
                    all_events.append(event)
                    print(f"    → {event.title[:80]}")
            else:
                print("No recent filings")

        print(f"\nFound {len(all_events)} SEC filings total")
        return all_events


# Add to EventSource enum in models/events.py
# SEC_EDGAR = "sec_edgar"


# Test the source
if __name__ == "__main__":
    source = SECEdgarSource()

    print("Testing SEC EDGAR source...")
    print("=" * 80)

    # Fetch 8-K filings (material events) from last 7 days
    events = source.fetch_all_companies(filing_type='8-K', days_back=7)

    print(f"\nCollected {len(events)} events:\n")
    for event in events:
        print(f"[{event.event_type.value.upper()}] {event.title}")
        print(f"  Published: {event.published_at}")
        print(f"  URL: {event.source_url}")
        print()
