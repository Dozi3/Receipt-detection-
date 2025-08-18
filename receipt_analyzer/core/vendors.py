"""Vendor mapping system with persistence and self-learning capabilities."""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from .config import get_default_vendor_map_path
from .logging_utils import get_logger


class VendorMap:
    """Vendor mapping with keyword-to-vendor mappings and learning capabilities."""
    
    def __init__(self):
        self.keywords: Dict[str, str] = {}
        self.ignored_domains: Set[str] = {
            'gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com', 
            'icloud.com', 'proton.me', 'live.com', 'msn.com'
        }
        self.synonyms: Dict[str, str] = {}
        self.auto_learned: Dict[str, datetime] = {}  # Track when keywords were learned
        self.manual_entries: Set[str] = set()  # Track manually added entries
        
        # Load built-in defaults
        self._load_builtin_mappings()
    
    def _load_builtin_mappings(self):
        """Load built-in vendor mappings."""
        builtin_keywords = {
            # Transport
            'dartcharge': 'Dartcharge',
            'ringgo': 'RingGo',
            'apcoa': 'APCOA',
            'national car parks': 'NCP',
            'ncp': 'NCP',
            
            # Retail
            'tesco': 'Tesco',
            'tesco stores': 'Tesco',
            'tesco express': 'Tesco',
            'sainsbury': 'Sainsburys',
            'sainsburys': 'Sainsburys',
            'asda': 'ASDA',
            'morrisons': 'Morrisons',
            'waitrose': 'Waitrose',
            'marks & spencer': 'M&S',
            'm&s': 'M&S',
            'john lewis': 'John Lewis',
            
            # Food & Drink
            'mcdonalds': 'McDonalds',
            'mcdonald': 'McDonalds',
            'starbucks': 'Starbucks',
            'costa': 'Costa Coffee',
            'costa coffee': 'Costa Coffee',
            'greggs': 'Greggs',
            'subway': 'Subway',
            'kfc': 'KFC',
            'burger king': 'Burger King',
            'pizza express': 'Pizza Express',
            'nandos': 'Nandos',
            
            # Fuel
            'shell': 'Shell',
            'bp': 'BP',
            'esso': 'Esso',
            'texaco': 'Texaco',
            'tesco petrol': 'Tesco Petrol',
            'sainsbury petrol': 'Sainsburys Petrol',
            
            # Services
            'royal mail': 'Royal Mail',
            'post office': 'Post Office',
            'argos': 'Argos',
            'boots': 'Boots',
            'superdrug': 'Superdrug',
            'currys': 'Currys',
            'pc world': 'Currys PC World',
            'amazon': 'Amazon',
        }
        
        self.keywords.update(builtin_keywords)
        
        # Built-in synonyms
        builtin_synonyms = {
            'Tesco Stores Ltd': 'Tesco',
            'Tesco Express': 'Tesco',
            'Sainsbury\'s Supermarkets Ltd': 'Sainsburys',
            'J Sainsbury': 'Sainsburys',
            'ASDA Stores Limited': 'ASDA',
            'Wm Morrison Supermarkets': 'Morrisons',
            'John Lewis Partnership': 'John Lewis',
        }
        
        self.synonyms.update(builtin_synonyms)
    
    def add_keyword(self, keyword: str, vendor: str, is_manual: bool = True, learned_time: Optional[datetime] = None):
        """Add a keyword-to-vendor mapping."""
        if not keyword or not vendor:
            return
        
        keyword_lower = keyword.lower().strip()
        vendor_clean = vendor.strip()
        
        self.keywords[keyword_lower] = vendor_clean
        
        if is_manual:
            self.manual_entries.add(keyword_lower)
        else:
            self.auto_learned[keyword_lower] = learned_time or datetime.now()
    
    def remove_keyword(self, keyword: str):
        """Remove a keyword mapping."""
        keyword_lower = keyword.lower().strip()
        
        if keyword_lower in self.keywords:
            del self.keywords[keyword_lower]
        
        if keyword_lower in self.auto_learned:
            del self.auto_learned[keyword_lower]
        
        if keyword_lower in self.manual_entries:
            self.manual_entries.remove(keyword_lower)
    
    def add_synonym(self, synonym: str, canonical: str):
        """Add a synonym mapping."""
        if not synonym or not canonical:
            return
        
        self.synonyms[synonym.strip()] = canonical.strip()
    
    def remove_synonym(self, synonym: str):
        """Remove a synonym mapping."""
        synonym = synonym.strip()
        if synonym in self.synonyms:
            del self.synonyms[synonym]
    
    def add_ignored_domain(self, domain: str):
        """Add a domain to the ignored list."""
        if domain:
            self.ignored_domains.add(domain.lower().strip())
    
    def remove_ignored_domain(self, domain: str):
        """Remove a domain from the ignored list."""
        domain = domain.lower().strip()
        if domain in self.ignored_domains:
            self.ignored_domains.remove(domain)
    
    def lookup_vendor(self, keyword: str) -> Optional[str]:
        """Look up vendor by keyword."""
        keyword_lower = keyword.lower().strip()
        return self.keywords.get(keyword_lower)
    
    def resolve_synonym(self, vendor: str) -> str:
        """Resolve vendor name through synonym mapping."""
        vendor = vendor.strip()
        return self.synonyms.get(vendor, vendor)
    
    def is_domain_ignored(self, domain: str) -> bool:
        """Check if a domain should be ignored."""
        return domain.lower().strip() in self.ignored_domains
    
    def get_all_keywords(self) -> Dict[str, str]:
        """Get all keyword mappings."""
        return self.keywords.copy()
    
    def get_manual_keywords(self) -> Dict[str, str]:
        """Get manually added keyword mappings."""
        return {k: v for k, v in self.keywords.items() if k in self.manual_entries}
    
    def get_auto_learned_keywords(self) -> Dict[str, str]:
        """Get automatically learned keyword mappings."""
        return {k: v for k, v in self.keywords.items() if k in self.auto_learned}
    
    def merge_from_dict(self, data: Dict):
        """Merge vendor mappings from a dictionary."""
        if 'keywords' in data and isinstance(data['keywords'], dict):
            for keyword, vendor in data['keywords'].items():
                self.add_keyword(keyword, vendor, is_manual=False)
        
        if 'ignored_domains' in data and isinstance(data['ignored_domains'], list):
            for domain in data['ignored_domains']:
                self.add_ignored_domain(domain)
        
        if 'synonyms' in data and isinstance(data['synonyms'], dict):
            for synonym, canonical in data['synonyms'].items():
                self.add_synonym(synonym, canonical)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'keywords': dict(self.keywords),
            'ignored_domains': list(self.ignored_domains),
            'synonyms': dict(self.synonyms),
            'metadata': {
                'auto_learned': {k: v.isoformat() for k, v in self.auto_learned.items()},
                'manual_entries': list(self.manual_entries),
                'export_time': datetime.now().isoformat(),
            }
        }
    
    def suggest_vendor_mapping(self, extracted_vendor: str, method: str) -> Optional[str]:
        """
        Suggest if a vendor mapping should be learned.
        
        Args:
            extracted_vendor: Vendor name extracted from receipt
            method: Method used to extract ('email', 'keyword', 'first_line')
        
        Returns:
            Suggested keyword if learning is recommended, None otherwise
        """
        if not extracted_vendor or method == 'keyword':
            # Don't suggest learning for keyword matches (already mapped)
            return None
        
        vendor_clean = extracted_vendor.strip()
        
        # Don't suggest if vendor is too generic
        generic_terms = {
            'receipt', 'invoice', 'bill', 'payment', 'total', 'unknown', 
            'email', 'store', 'shop', 'ltd', 'limited', 'inc', 'corp'
        }
        
        if vendor_clean.lower() in generic_terms:
            return None
        
        # Don't suggest if vendor is too short or too long
        if len(vendor_clean) < 3 or len(vendor_clean) > 50:
            return None
        
        # For email domain extractions, suggest the domain as keyword
        if method == 'email':
            # Use the vendor name as both keyword and value
            return vendor_clean.lower()
        
        # For first line extractions, suggest if vendor looks like a company name
        if method == 'first_line':
            # Simple heuristic: contains letters and reasonable length
            if any(c.isalpha() for c in vendor_clean) and 3 <= len(vendor_clean) <= 30:
                return vendor_clean.lower()
        
        return None


def load_vendor_map(file_path: Optional[Path] = None) -> VendorMap:
    """Load vendor mappings from JSON file."""
    if file_path is None:
        file_path = get_default_vendor_map_path()
    
    vendor_map = VendorMap()
    logger = get_logger()
    
    if not file_path.exists():
        logger.info(f"No vendor map found at {file_path}, using defaults")
        return vendor_map
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        vendor_map.merge_from_dict(data)
        
        # Restore metadata if present
        if 'metadata' in data and isinstance(data['metadata'], dict):
            metadata = data['metadata']
            
            if 'manual_entries' in metadata:
                vendor_map.manual_entries = set(metadata['manual_entries'])
            
            if 'auto_learned' in metadata:
                for keyword, time_str in metadata['auto_learned'].items():
                    try:
                        learned_time = datetime.fromisoformat(time_str)
                        vendor_map.auto_learned[keyword] = learned_time
                    except ValueError:
                        pass
        
        logger.info(f"Loaded vendor map with {len(vendor_map.keywords)} keywords from {file_path}")
        return vendor_map
    
    except (json.JSONDecodeError, OSError) as e:
        logger.warn(f"Failed to load vendor map from {file_path}: {e}")
        return vendor_map


def save_vendor_map(vendor_map: VendorMap, file_path: Optional[Path] = None) -> bool:
    """Save vendor mappings to JSON file."""
    if file_path is None:
        file_path = get_default_vendor_map_path()
    
    logger = get_logger()
    
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(vendor_map.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved vendor map with {len(vendor_map.keywords)} keywords to {file_path}")
        return True
    
    except OSError as e:
        logger.warn(f"Failed to save vendor map to {file_path}: {e}")
        return False


def export_vendor_map_csv(vendor_map: VendorMap, csv_path: Path) -> bool:
    """Export vendor mappings to CSV file."""
    logger = get_logger()
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Keyword', 'Vendor', 'Type', 'Added'])
            
            for keyword, vendor in sorted(vendor_map.keywords.items()):
                if keyword in vendor_map.manual_entries:
                    entry_type = 'Manual'
                    added = 'User Added'
                elif keyword in vendor_map.auto_learned:
                    entry_type = 'Auto-learned'
                    added = vendor_map.auto_learned[keyword].strftime('%Y-%m-%d')
                else:
                    entry_type = 'Built-in'
                    added = 'Default'
                
                writer.writerow([keyword, vendor, entry_type, added])
        
        logger.info(f"Exported {len(vendor_map.keywords)} vendor mappings to {csv_path}")
        return True
    
    except OSError as e:
        logger.warn(f"Failed to export vendor map to {csv_path}: {e}")
        return False


def import_vendor_map_csv(csv_path: Path) -> VendorMap:
    """Import vendor mappings from CSV file."""
    logger = get_logger()
    vendor_map = VendorMap()
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            imported_count = 0
            for row in reader:
                keyword = row.get('Keyword', '').strip()
                vendor = row.get('Vendor', '').strip()
                
                if keyword and vendor:
                    vendor_map.add_keyword(keyword, vendor, is_manual=True)
                    imported_count += 1
        
        logger.info(f"Imported {imported_count} vendor mappings from {csv_path}")
        return vendor_map
    
    except (OSError, csv.Error) as e:
        logger.warn(f"Failed to import vendor map from {csv_path}: {e}")
        return VendorMap()


def merge_vendor_maps(base_map: VendorMap, *other_maps: VendorMap) -> VendorMap:
    """Merge multiple vendor maps, with later maps taking precedence."""
    merged = VendorMap()
    
    # Start with base map
    merged.keywords.update(base_map.keywords)
    merged.ignored_domains.update(base_map.ignored_domains)
    merged.synonyms.update(base_map.synonyms)
    merged.auto_learned.update(base_map.auto_learned)
    merged.manual_entries.update(base_map.manual_entries)
    
    # Merge other maps
    for other_map in other_maps:
        merged.keywords.update(other_map.keywords)
        merged.ignored_domains.update(other_map.ignored_domains)
        merged.synonyms.update(other_map.synonyms)
        merged.auto_learned.update(other_map.auto_learned)
        merged.manual_entries.update(other_map.manual_entries)
    
    return merged