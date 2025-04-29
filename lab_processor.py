import re

def extract_lab_tests(extracted_text_data):
    """
    Process extracted text data to identify lab tests, values, and ranges
    
    Args:
        extracted_text_data: List of dictionaries with text and position info
    
    Returns:
        List of dictionaries with lab test information
    """
    # Group text elements that are likely on the same line
    lines = group_by_lines(extracted_text_data)
    
    # Extract lab tests from these grouped lines
    lab_tests = []
    for i, line_elements in enumerate(lines):
        # Join elements in the same line
        line_text = " ".join([elem["text"] for elem in line_elements])
        
        # Look for test name and value patterns
        test_match = re.search(r'([A-Z][A-Za-z\s()]+)(?:\s+)(\d+\.?\d*)\s*(\w+)?', line_text)
        
        if test_match:
            test_name = test_match.group(1).strip()
            test_value = test_match.group(2)
            test_unit = test_match.group(3) if test_match.group(3) else ""
            
            # Search for reference range in current and next lines
            reference_range = find_reference_range(line_text, lines, i)
            
            # Determine if out of range
            out_of_range = is_out_of_range(test_value, reference_range)
            
            lab_test = {
                "test_name": test_name,
                "test_value": test_value,
                "bio_reference_range": reference_range,
                "test_unit": test_unit,
                "lab_test_out_of_range": out_of_range
            }
            
            lab_tests.append(lab_test)
    
    return lab_tests

def group_by_lines(text_elements, y_threshold=10):
    """Group text elements that are on the same line based on y-coordinate"""
    if not text_elements:
        return []
    
    # Sort by y-position
    sorted_elements = sorted(text_elements, key=lambda x: x["position"]["y"])
    
    lines = []
    current_line = [sorted_elements[0]]
    current_y = sorted_elements[0]["position"]["y"]
    
    for element in sorted_elements[1:]:
        if abs(element["position"]["y"] - current_y) <= y_threshold:
            # Same line
            current_line.append(element)
        else:
            # New line
            # Sort elements in the line by x position
            current_line.sort(key=lambda x: x["position"]["x"])
            lines.append(current_line)
            current_line = [element]
            current_y = element["position"]["y"]
    
    if current_line:
        current_line.sort(key=lambda x: x["position"]["x"])
        lines.append(current_line)
    
    return lines

def find_reference_range(current_line, all_lines, current_index):
    """Search for reference range in current and next lines"""
    # Search in current line
    range_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', current_line)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"
    
    # Search in next 2 lines
    for j in range(1, 3):
        if current_index + j < len(all_lines):
            next_line = " ".join([elem["text"] for elem in all_lines[current_index + j]])
            range_match = re.search(r'(?:Reference|Normal|Range):?\s*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', next_line)
            if range_match:
                return f"{range_match.group(1)}-{range_match.group(2)}"
            
            # Try simple number range
            range_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', next_line)
            if range_match:
                return f"{range_match.group(1)}-{range_match.group(2)}"
    
    return ""

def is_out_of_range(value, reference_range):
    """Determine if test value is outside reference range"""
    if not reference_range:
        return False
    
    try:
        test_val = float(value)
        low_ref, high_ref = map(float, reference_range.split('-'))
        return test_val < low_ref or test_val > high_ref
    except (ValueError, TypeError):
        return False