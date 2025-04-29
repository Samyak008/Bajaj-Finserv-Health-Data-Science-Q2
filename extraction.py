import io
import cv2
import numpy as np
import easyocr
from PIL import Image

# Initialize the OCR reader once
reader = easyocr.Reader(['en'])

def extract_text_from_image(image_bytes):
    """
    Extract raw text content from an image using EasyOCR
    
    Args:
        image_bytes: Binary image data
    
    Returns:
        List of dictionaries with text and position information
    """
    # Convert binary data to image
    image = Image.open(io.BytesIO(image_bytes))
    image_np = np.array(image)
    
    # Convert to grayscale if needed
    if len(image_np.shape) == 3 and image_np.shape[2] == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_np
    
    # Extract text using EasyOCR
    # Format: [[bbox, text, confidence], ...]
    results = reader.readtext(gray)
    
    # Format results as structured JSON
    extracted_data = []
    for detection in results:
        bbox = detection[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        text = detection[1]
        confidence = float(detection[2])
        
        # Calculate y-position for sorting (average of y-coordinates)
        y_position = (bbox[0][1] + bbox[1][1] + bbox[2][1] + bbox[3][1]) / 4
        
        # Calculate x-position for sorting (average of x-coordinates)
        x_position = (bbox[0][0] + bbox[1][0] + bbox[2][0] + bbox[3][0]) / 4
        
        extracted_data.append({
            "text": text,
            "confidence": confidence,
            "position": {
                "x": x_position,
                "y": y_position,
                "bbox": bbox
            }
        })
    
    # Sort by vertical position (top to bottom)
    extracted_data.sort(key=lambda x: x["position"]["y"])
    
    return extracted_data