"""
OneDrive URL Parser and File Lister
===================================

Utility to extract file information from OneDrive shared folder URLs.
Provides read-only access to file listings without editing online files.

Supports URLs like:
https://1drv.ms/f/c/0de835881591763e/Ej52kRWINegggA3jDQIAAAABymzoY0BNi6VWqqlifiJgRw?e=ZKiFKs

Usage:
  python utils/onedrive_parser.py --url "https://1drv.ms/f/..." --output files.json
"""

import argparse
import json
import re
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

class OneDriveParser:
    """Parser for OneDrive shared folder URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_folder_info(self, url: str) -> Dict[str, Any]:
        """Extract folder information from OneDrive URL"""
        try:
            # Parse URL components
            parsed = urlparse(url)
            
            # Extract folder ID from path
            path_parts = parsed.path.split('/')
            folder_info = {
                'original_url': url,
                'domain': parsed.netloc,
                'path_parts': path_parts,
                'query_params': parse_qs(parsed.query)
            }
            
            # Try to extract folder ID
            if len(path_parts) >= 4:
                folder_info['folder_id'] = path_parts[3]
            
            return folder_info
            
        except Exception as e:
            return {'error': f'Failed to parse URL: {e}'}
    
    def get_file_list_web_scraping(self, url: str) -> List[Dict[str, Any]]:
        """
        Attempt to get file list via web scraping
        NOTE: This is a basic implementation - OneDrive may require authentication
        """
        files = []
        
        try:
            # Make request to the shared folder
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                content = response.text
                
                # Look for file patterns in the HTML
                # OneDrive typically embeds file info in JSON or data attributes
                
                # Pattern 1: Look for file names in common formats
                file_patterns = [
                    r'"name":\s*"([^"]+\.(?:pdf|epub|mobi|doc|docx|txt))"',
                    r'data-file-name="([^"]+\.(?:pdf|epub|mobi|doc|docx|txt))"',
                    r'title="([^"]+\.(?:pdf|epub|mobi|doc|docx|txt))"'
                ]
                
                for pattern in file_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match not in [f['name'] for f in files]:
                            files.append({
                                'name': match,
                                'type': 'file',
                                'extension': Path(match).suffix.lower(),
                                'source': 'web_scraping'
                            })
                
                # Pattern 2: Look for JSON data embedded in page
                json_pattern = r'window\._cfg\s*=\s*({.*?});'
                json_match = re.search(json_pattern, content, re.DOTALL)
                
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1))
                        # Extract file information from JSON if available
                        files.extend(self.extract_files_from_json(json_data))
                    except json.JSONDecodeError:
                        pass
            
            else:
                print(f"HTTP {response.status_code}: Could not access OneDrive folder")
                
        except requests.RequestException as e:
            print(f"Request failed: {e}")
        
        return files
    
    def extract_files_from_json(self, json_data: Dict) -> List[Dict[str, Any]]:
        """Extract file information from embedded JSON data"""
        files = []
        
        # OneDrive JSON structure varies, try common patterns
        def search_json_recursive(obj, files_list):
            if isinstance(obj, dict):
                # Look for file-like objects
                if 'name' in obj and 'size' in obj:
                    name = obj.get('name', '')
                    if any(name.lower().endswith(ext) for ext in ['.pdf', '.epub', '.mobi', '.doc', '.docx', '.txt']):
                        files_list.append({
                            'name': name,
                            'size': obj.get('size', 0),
                            'type': 'file',
                            'extension': Path(name).suffix.lower(),
                            'source': 'json_extraction'
                        })
                
                # Recursively search nested objects
                for key, value in obj.items():
                    if key in ['files', 'items', 'children', 'content']:
                        search_json_recursive(value, files_list)
                        
            elif isinstance(obj, list):
                for item in obj:
                    search_json_recursive(item, files_list)
        
        search_json_recursive(json_data, files)
        return files
    
    def generate_predictions_from_filenames(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate metadata predictions from filenames"""
        predictions = []
        
        for file_info in files:
            filename = file_info['name']
            
            # Extract title, author, year from filename using patterns
            prediction = {
                'filename': filename,
                'predicted_title': self.extract_title_from_filename(filename),
                'predicted_author': self.extract_author_from_filename(filename),
                'predicted_year': self.extract_year_from_filename(filename),
                'file_extension': file_info.get('extension', ''),
                'file_size': file_info.get('size', 0),
                'confidence': self.calculate_filename_confidence(filename),
                'source': 'onedrive_prediction'
            }
            
            predictions.append(prediction)
        
        return predictions
    
    def extract_title_from_filename(self, filename: str) -> Optional[str]:
        """Extract probable title from filename"""
        name_without_ext = Path(filename).stem
        
        # Common patterns: "Author - Title" or "Title - Author"
        if ' - ' in name_without_ext:
            parts = name_without_ext.split(' - ')
            if len(parts) >= 2:
                # Assume first part is author if it looks like a name
                first_part = parts[0].strip()
                if len(first_part.split()) <= 3:  # Probably author name
                    return parts[1].strip()
                else:  # Probably title
                    return first_part
        
        # Remove common prefixes/suffixes
        cleaned = name_without_ext.replace('_', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else None
    
    def extract_author_from_filename(self, filename: str) -> Optional[str]:
        """Extract probable author from filename"""
        name_without_ext = Path(filename).stem
        
        if ' - ' in name_without_ext:
            parts = name_without_ext.split(' - ')
            if len(parts) >= 2:
                first_part = parts[0].strip()
                if len(first_part.split()) <= 3:  # Probably author name
                    return first_part
        
        return None
    
    def extract_year_from_filename(self, filename: str) -> Optional[int]:
        """Extract probable year from filename"""
        # Look for 4-digit years
        year_patterns = [
            r'\((\d{4})\)',  # (2023)
            r'(\d{4})\.(?:pdf|epub|mobi)',  # 2023.pdf
            r'\s(\d{4})\s',  # space 2023 space
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, filename)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2030:
                    return year
        
        return None
    
    def calculate_filename_confidence(self, filename: str) -> float:
        """Calculate confidence score based on filename quality"""
        confidence = 0.1  # Base confidence
        
        # Bonus for structured naming
        if ' - ' in filename:
            confidence += 0.3
        
        # Bonus for year present
        if self.extract_year_from_filename(filename):
            confidence += 0.2
            
        # Bonus for recognized extension
        if Path(filename).suffix.lower() in ['.pdf', '.epub', '.mobi']:
            confidence += 0.2
            
        # Penalty for very short or messy names
        name_without_ext = Path(filename).stem
        if len(name_without_ext.replace('_', ' ').split()) < 2:
            confidence -= 0.1
        
        return min(max(confidence, 0.1), 0.8)

def main():
    parser = argparse.ArgumentParser(
        description='OneDrive URL Parser - Extract file listings from shared folders',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils/onedrive_parser.py --url "https://1drv.ms/f/..." --output files.json
  python utils/onedrive_parser.py --url "https://1drv.ms/f/..." --format predictions
  python utils/onedrive_parser.py --url "https://1drv.ms/f/..." --dry-run
        """
    )
    
    parser.add_argument('--url', required=True,
                       help='OneDrive shared folder URL')
    
    parser.add_argument('--output', type=str, default='onedrive_files.json',
                       help='Output file path (default: onedrive_files.json)')
    
    parser.add_argument('--format', choices=['files', 'predictions'], default='files',
                       help='Output format: files or predictions (default: files)')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be extracted without saving')
    
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Initialize parser
    parser_instance = OneDriveParser()
    
    print(f"Analyzing OneDrive URL: {args.url}")
    
    # Extract folder info
    folder_info = parser_instance.extract_folder_info(args.url)
    
    if 'error' in folder_info:
        print(f"Error: {folder_info['error']}")
        return 1
    
    print(f"Domain: {folder_info['domain']}")
    if 'folder_id' in folder_info:
        print(f"Folder ID: {folder_info['folder_id']}")
    
    # Get file list
    print("Attempting to extract file list...")
    files = parser_instance.get_file_list_web_scraping(args.url)
    
    if not files:
        print("No files found. OneDrive may require authentication or the URL may be private.")
        print("Try:")
        print("1. Make sure the folder is publicly shared")
        print("2. Use OneDrive API with proper authentication") 
        print("3. Manually create file list from browser view")
        return 1
    
    print(f"Found {len(files)} files")
    
    # Generate output based on format
    if args.format == 'predictions':
        output_data = parser_instance.generate_predictions_from_filenames(files)
        print("Generated metadata predictions for files")
    else:
        output_data = files
    
    # Show sample
    print("\nSample files found:")
    for i, item in enumerate(output_data[:5]):
        if args.format == 'predictions':
            print(f"  {i+1}. {item['filename']}")
            if item['predicted_title']:
                print(f"      Title: {item['predicted_title']}")
            if item['predicted_author']:
                print(f"      Author: {item['predicted_author']}")
            print(f"      Confidence: {item['confidence']:.2f}")
        else:
            print(f"  {i+1}. {item['name']} ({item.get('size', 'unknown size')})")
    
    if len(output_data) > 5:
        print(f"  ... and {len(output_data) - 5} more")
    
    # Save output
    if not args.dry_run:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nOutput saved to: {output_path}")
        print(f"Format: {args.format}")
        print(f"Total items: {len(output_data)}")
    else:
        print(f"\nDry run complete. Would save {len(output_data)} items to {args.output}")
    
    return 0

if __name__ == '__main__':
    exit(main())