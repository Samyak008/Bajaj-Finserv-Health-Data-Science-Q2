import re

def extract_lab_tests(extracted_text_data):
    """
    Process extracted text data to identify lab tests, values, and ranges
    
    Args:
        extracted_text_data: List of dictionaries with text and position info
    
    Returns:
        List of dictionaries with lab test information
    """
    # Group text elements into rows
    rows = group_by_rows(extracted_text_data)
    
    # Try to identify if this is a tabular report
    header_info = find_table_header(rows)
    
    if header_info:
        # Process as a table with columns
        return process_tabular_report(rows, header_info)
    else:
        # Fallback to processing as a list of tests
        return process_list_report(rows)

def find_table_header(rows):
    """Identify table header row and column positions"""
    header_keywords = {
        'test_name': ['parameter', 'investigation', 'test', 'examination'],
        'specimen': ['specimen', 'sample'],
        'value': ['result', 'value', 'observed'],
        'unit': ['unit'],
        'range': ['reference', 'interval', 'range', 'biological', 'normal']
    }
    
    for i, row in enumerate(rows):
        if not row or len(row) < 2:
            continue
            
        # Check if this row contains header keywords
        row_text = " ".join([item["text"].lower() for item in row])
        header_matches = 0
        column_info = {'row_index': i, 'columns': {}}
        
        # Check if multiple header keywords are present
        for col_type, keywords in header_keywords.items():
            for kw in keywords:
                if kw in row_text:
                    header_matches += 1
                    break
        
        # If at least 2 header keywords are found, consider this a header row
        if header_matches >= 2:
            # Find x-positions of each column
            for item in row:
                text = item["text"].lower()
                pos_x = item["position"]["x"]
                
                for col_type, keywords in header_keywords.items():
                    if any(kw in text for kw in keywords):
                        column_info['columns'][col_type] = pos_x
                        break
            
            # If we found positions for at least test_name and value, this is a valid header
            if 'test_name' in column_info['columns'] and ('value' in column_info['columns'] or 
                                                           'range' in column_info['columns']):
                return column_info
    
    return None

def process_tabular_report(rows, header_info):
    """Process a report with a table structure"""
    lab_tests = []
    header_row_index = header_info['row_index']
    col_positions = header_info['columns']
    
    # Process each row after the header
    for i in range(header_row_index + 1, len(rows)):
        row = rows[i]
        if not row or len(row) < 2:
            continue
            
        # Skip non-test rows like headers, footers, etc.
        row_text = " ".join([item["text"] for item in row]).upper()
        if any(marker in row_text for marker in 
              ["END OF REPORT", "SPECIMEN", "NOTE:", "TESTER", "PRINTED BY"]):
            continue
            
        # Extract test information from this row
        test_info = extract_test_from_tabular_row(row, col_positions)
        if test_info:
            lab_tests.append(test_info)
    
    return lab_tests

def extract_test_from_tabular_row(row, col_positions):
    """Extract test information from a row in tabular format"""
    # Initialize test data
    test_data = {
        "test_name": "",
        "test_value": "",
        "bio_reference_range": "",
        "test_unit": "",
        "lab_test_out_of_range": False
    }
    
    # Group row items by closest column
    column_items = {col: [] for col in col_positions.keys()}
    
    for item in row:
        if not item["text"].strip():
            continue
            
        # Find the closest column for this item
        min_distance = float('inf')
        closest_col = None
        x_pos = item["position"]["x"]
        
        for col, pos in col_positions.items():
            dist = abs(x_pos - pos)
            if dist < min_distance:
                min_distance = dist
                closest_col = col
        
        if closest_col:
            column_items[closest_col].append(item["text"])
    
    # Extract test name
    if 'test_name' in column_items and column_items['test_name']:
        test_data["test_name"] = " ".join(column_items['test_name']).strip()
    else:
        return None  # No test name found, skip this row
    
    # Extract test value
    if 'value' in column_items and column_items['value']:
        value_text = " ".join(column_items['value']).strip()
        # Extract numeric value (remove any H/L markers)
        value_match = re.search(r'(\d+\.?\d*)', value_text)
        if value_match:
            test_data["test_value"] = value_match.group(1)
        else:
            test_data["test_value"] = value_text
    
    # Extract reference range and unit
    range_text = ""
    if 'range' in column_items and column_items['range']:
        range_text = " ".join(column_items['range']).strip()
        
        # Extract reference range pattern like "0-1.4 mg/dL"
        range_unit_pattern = r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*([a-zA-Z/%]+)?'
        range_match = re.search(range_unit_pattern, range_text)
        
        if range_match:
            low = range_match.group(1)
            high = range_match.group(2)
            test_data["bio_reference_range"] = f"{low}-{high}"
            
            # Extract unit from reference range if present
            if range_match.group(3):
                test_data["test_unit"] = range_match.group(3).strip()
    
    # If unit not found in range, check unit column
    if not test_data["test_unit"] and 'unit' in column_items and column_items['unit']:
        test_data["test_unit"] = " ".join(column_items['unit']).strip()
    
    # Clean up unit (handle common OCR issues)
    test_data["test_unit"] = clean_unit(test_data["test_unit"])
    
    # Determine if test is out of range
    test_data["lab_test_out_of_range"] = is_out_of_range(
        test_data["test_value"], test_data["bio_reference_range"]
    )
    
    return test_data

def process_list_report(rows):
    """Process a report formatted as a list rather than a table"""
    lab_tests = []
    
    for i, row in enumerate(rows):
        if not row or len(row) < 2:
            continue
            
        row_text = " ".join([item["text"] for item in row])
        
        # Skip header/footer rows
        if any(marker in row_text.upper() for marker in 
              ["END OF REPORT", "SPECIMEN", "NOTE:", "TESTER", "PRINTED BY"]):
            continue
        
        # Try to match test name followed by value pattern
        test_match = re.search(r'([A-Za-z\s\/\(\)]+)\s+(\d+\.?\d*)\s*([A-Za-z%\/]+)?', row_text)
        
        if test_match:
            test_name = test_match.group(1).strip()
            test_value = test_match.group(2)
            test_unit = test_match.group(3) if test_match.group(3) else ""
            
            # Look for reference range in this row or next rows
            reference_range = find_reference_range(row_text, rows, i)
            
            lab_test = {
                "test_name": test_name,
                "test_value": test_value,
                "bio_reference_range": reference_range,
                "test_unit": clean_unit(test_unit),
                "lab_test_out_of_range": is_out_of_range(test_value, reference_range)
            }
            
            lab_tests.append(lab_test)
    
    return lab_tests

def find_reference_range(text, rows, current_row_index):
    """Find reference range in text or in nearby rows"""
    # First try in current text
    range_match = re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)', text)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"
    
    # Look in next row
    if current_row_index + 1 < len(rows):
        next_row_text = " ".join([item["text"] for item in rows[current_row_index + 1]])
        range_match = re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)', next_row_text)
        if range_match:
            return f"{range_match.group(1)}-{range_match.group(2)}"
    
    return ""

def is_out_of_range(value, reference_range):
    """Determine if a test value is outside its reference range"""
    if not reference_range or not value:
        return False
    
    try:
        test_val = float(value)
        # Parse range in format "low-high"
        if '-' in reference_range:
            low_str, high_str = reference_range.split('-')
            # Clean and convert to float
            low = float(re.search(r'(\d+\.?\d*)', low_str).group(1))
            high = float(re.search(r'(\d+\.?\d*)', high_str).group(1))
            return test_val < low or test_val > high
    except (ValueError, AttributeError):
        pass
    
    return False

def clean_unit(unit):
    """Clean and standardize unit text"""
    if not unit:
        return ""
        
    # Standardize common units
    unit = unit.strip()
    
    # Fix scientific notation
    if re.search(r'10[\^x]?\d+/[uμ]L', unit):
        match = re.search(r'10[\^x]?(\d+)/([uμ]L)', unit)
        if match:
            return f"10^{match.group(1)}/{match.group(2)}"
    
    # Fix common OCR errors
    replacements = {
        'gldL': 'g/dL', 
        'g/dl': 'g/dL',
        'mg/dl': 'mg/dL',
        'u/l': 'U/L',
        'u/L': 'U/L'
    }
    
    for wrong, correct in replacements.items():
        if unit.lower() == wrong.lower():
            return correct
    
    return unit

def group_by_rows(text_elements, y_threshold=15):
    """Group text elements into rows based on y-coordinate"""
    if not text_elements:
        return []
    
    # Sort by y-position
    sorted_elements = sorted(text_elements, key=lambda x: x["position"]["y"])
    
    rows = []
    current_row = [sorted_elements[0]]
    current_y = sorted_elements[0]["position"]["y"]
    
    for element in sorted_elements[1:]:
        if abs(element["position"]["y"] - current_y) <= y_threshold:
            # Same row
            current_row.append(element)
        else:
            # New row
            # Sort elements in the row by x position
            current_row.sort(key=lambda x: x["position"]["x"])
            rows.append(current_row)
            current_row = [element]
            current_y = element["position"]["y"]
    
    if current_row:
        current_row.sort(key=lambda x: x["position"]["x"])
        rows.append(current_row)
    
    return rows