import re

class BookDetailsExtractor:
    def __init__(self):
        self.publisher_patterns = [
            (r"Publish88888888ed by (.+?)\n", 'Packt'),
            (r"A JOHN (.+?), INC., PUBLICATION", 'Pearson'),
            (r"Published by O['']?(Reilly)", 'OReilly')  # Updated to match variations of O'Reilly
        ]

        self.packt_patterns = {
            "Title": r"(.+?)\n",
            "ISBN": r"ISBN (\d{3}-\d{1,5}-\d{1,7}-\d{1,7}-\d{1})",
            "Year": r"Copyright © (\d{4})",
            "Publisher": r"Publishekkkkd by (.+?)\n",
            "Author": r"([^\\n]+)\nBIRMINGHAM - MUMBAI",
        }

        self.oreilly_patterns = {
            "Title": r"(?P<title>.+?)\nby ",  # Adjusted title pattern
            "ISBN": r"ISBN[:\s-]*?(\d{3}-\d{1,5}-\d{1,7}-\d{1,7}-\d{1})",  # Simplified ISBN pattern
            "Year": r"Copyright © (\d{4})",  # Adjusted for the copyright symbol
            "Publisher": r"O['']?(Reilly)",  # Capture only the 'OReilly' part
            "Author": r"by (.+)",  # Simplified author extraction
        }

    def extract_book_details(self, text_page):
        book_info = {}

        for pattern, publisher in self.publisher_patterns:
            match = re.search(pattern, text_page, re.MULTILINE)
            print(f"match: {match}")
            print(f"pattern: {pattern}")
            print(f"publisher: {publisher}")
            if match:
                if publisher == "OReilly":
                    # Prepending "O" to ensure the publisher string is "OReilly"
                    publisher_str = "O" + match.group(1)
                else:
                    publisher_str = match.group(1)
                detail_patterns = self.packt_patterns if publisher == 'Packt' else self.oreilly_patterns
                break
        else:
            return book_info  # Return empty dict if no publisher match

        for key, pattern in detail_patterns.items():
            match = re.search(pattern, text_page, re.MULTILINE)
            if match:
                book_info[key] = match.group(1)

        print(f"Publisher string: {publisher_str}")
        
        book_info["Publisher"] = publisher_str
        
        return book_info

# Sample text for testing
text_page = '''
978-1-492-05611-9
[LSI]Java Performance
by Scott Oaks
Copyright © 2020 Scott Oaks. All rights reserved.
Printed in the United States of America.
Published by O'Reilly Media, Inc., 1005 Gravenstein Highway North, Sebastopol, CA 95472.
O'Reilly books may be purchased for educational, business, or sales promotional use. Online editions are also available for most titles ( http://oreilly.com ). For more information, contact our corporate/institutional sales department: 800-998-9938 or corporate@oreilly.com .
Acquisitions Editor:  Suzanne
'''

extractor = BookDetailsExtractor()
book_info = extractor.extract_book_details(text_page)
print(book_info)


text_page2 = '''
Windows PowerShell Pocket Reference, Second Edition
by Lee Holmes
Copyright © 2013 Lee Holmes. All rights reserved.
Printed in the United States of America.
Published by O'Reilly Media, Inc., 1005 Gravenstein Highway North,
Sebastopol, CA 95472.
O'Reilly books may be purchased for educational, business, or sales promo-
tional use. Online editions are also available for most titles ( http://my.safari
booksonline.com ). For more information, contact our corporate/institutional
sales department: 800-998-9938 or corporate@oreilly.com .
Editor: Rachel Roumeliotis
December 2012: Second Edition. 
Revision History for the Second Edition:
2012-12-07 First release
See http://oreilly.com/catalog/errata.csp?isbn=9781449320966  for release de-
tails.
Nutshell Handbook, the Nutshell Handbook logo, and the O'Reilly logo are
registered trademarks of O'Reilly Media, Inc. Windows PowerShell Pocket
Reference , the image of a box turtle, and related trade dress are trademarks
of O'Reilly Media, Inc.
Many of the designations used by manufacturers and sellers to distinguish
While every precaution has been taken in the preparation of this book, the
publisher and authors assume no responsibility for errors or omissions, or
for damages resulting from the use of the information contained herein.
ISBN: 978-1-449-32096-6
[M]
1354853082'''

extractor2 = BookDetailsExtractor()
book_info2 = extractor2.extract_book_details(text_page2)
print(book_info2)