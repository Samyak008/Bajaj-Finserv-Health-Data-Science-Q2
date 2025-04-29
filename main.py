import os
import sys
import argparse
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import json
from extraction import extract_text_from_image
from lab_processor import extract_lab_tests

app = FastAPI(title="Lab Report Processor API")

@app.post("/get-lab-tests")
async def get_lab_tests(file: UploadFile = File(...)):
    try:
        # Check if file is an image
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image content
        contents = await file.read()
        
        # Step 1: Extract raw text from image
        extracted_text = extract_text_from_image(contents)
        
        # Step 2: Process extracted text to identify lab tests
        lab_test_data = extract_lab_tests(extracted_text)
        
        return {"is_success": True, "data": lab_test_data}
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"is_success": False, "error": str(e)}
        )

def process_image_file(image_path):
    """Process an image file from a local path"""
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            print(f"Error: File not found - {image_path}")
            return
        
        # Check file extension
        _, ext = os.path.splitext(image_path)
        if ext.lower() not in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
            print(f"Error: File must be an image - {image_path}")
            return
        
        # Read image content
        with open(image_path, 'rb') as file:
            contents = file.read()
        
        # Step 1: Extract raw text from image
        print(f"Processing image: {image_path}")
        extracted_text = extract_text_from_image(contents)
        
        # Step 2: Process extracted text to identify lab tests
        lab_test_data = extract_lab_tests(extracted_text)
        
        # Format and print results
        result = {"is_success": True, "data": lab_test_data}
        print(json.dumps(result, indent=2))
        
        return result
    
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return {"is_success": False, "error": str(e)}

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Lab Report Processor')
    parser.add_argument('--image', type=str, help='Path to the image file to process')
    parser.add_argument('--server', action='store_true', help='Run as FastAPI server')
    
    args = parser.parse_args()
    
    # If image path is provided, process it
    if args.image:
        process_image_file(args.image)
    # If server flag is provided or no arguments given, start the server
    elif args.server or len(sys.argv) == 1:
        print("Starting FastAPI server...")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        parser.print_help()