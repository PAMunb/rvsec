#!/usr/bin/env python3
"""
Advanced Android Screenshot Analyzer

Efficiently extracts information from Android screenshots with
optimized text and error detection.

Dependencies (Ubuntu):
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    python3-pip \
    libopencv-dev \
    python3-opencv
pip3 install \
    pytesseract \
    opencv-python \
    Pillow \
    numpy
"""

import cv2
import numpy as np
import pytesseract
import json
import sys
from typing import Dict, List, Any
from PIL import Image


class ScreenshotAnalyzer:
    def __init__(self, image_path: str):
        """
        Initialize the screenshot analyzer with image preprocessing.

        Args:
            image_path (str): Path to the screenshot image
        """
        # Read image in color for full color analysis
        self.original_image = cv2.imread(image_path)

        # Validate image loading
        if self.original_image is None:
            raise ValueError(f"Could not read image from path: {image_path}")

        # Create preprocessed images for different analyses
        self.gray_image = self._preprocess_grayscale(self.original_image)
        self.binary_image = self._preprocess_binary(self.original_image)

    def _preprocess_grayscale(self, image):
        """
        Convert image to grayscale with enhanced contrast.

        Args:
            image (np.ndarray): Original color image

        Returns:
            np.ndarray: Grayscale image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply histogram equalization to improve contrast
        return cv2.equalizeHist(gray)

    def _preprocess_binary(self, image):
        """
        Create a binary image with adaptive thresholding.

        Args:
            image (np.ndarray): Original color image

        Returns:
            np.ndarray: Binary image
        """
        # Convert to grayscale first
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

    def extract_text(self) -> List[Dict[str, Any]]:
        """
        Extract text using multiple OCR techniques.

        Returns:
            List of dictionaries with text and its coordinates
        """
        # Multiple Tesseract configurations for robust text detection
        configs = [
            # High precision mode with full character set
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?() -c preserve_interword_spaces=1',
            # Page segmentation mode for single uniform block of text
            r'--oem 3 --psm 11'
        ]

        texts = []
        for config in configs:
            # Try OCR with different configurations
            try:
                text_data = pytesseract.image_to_data(
                    self.gray_image,
                    output_type=pytesseract.Output.DICT,
                    config=config
                )

                # Process and filter text results
                for i in range(len(text_data['text'])):
                    # Stricter filtering of text
                    if (int(text_data['conf'][i]) > 50 and
                            len(text_data['text'][i].strip()) > 1):
                        texts.append({
                            'text': text_data['text'][i].strip(),
                            'confidence': int(text_data['conf'][i]),
                            'bbox': {
                                'x': int(text_data['left'][i]),
                                'y': int(text_data['top'][i]),
                                'width': int(text_data['width'][i]),
                                'height': int(text_data['height'][i])
                            }
                        })
            except Exception as e:
                print(f"OCR configuration failed: {e}")

        return texts

    def detect_buttons(self) -> List[Dict[str, Any]]:
        """
        Detect potential button regions using contour analysis.

        Returns:
            List of button characteristics
        """
        # Find contours in binary image
        contours, _ = cv2.findContours(
            self.binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        buttons = []
        for contour in contours:
            # Filter contours to identify potential buttons
            area = cv2.contourArea(contour)
            if 50 < area < 5000:  # Adjust area range as needed
                x, y, w, h = cv2.boundingRect(contour)
                buttons.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': area
                })

        return buttons

    def detect_error_indicators(self) -> List[Dict[str, Any]]:
        """
        Detect error indicators typically shown in red.

        Returns:
            List of error indicator characteristics
        """
        # Convert to HSV for better color detection
        hsv_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2HSV)

        # Define red color ranges in HSV
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        # Create masks for red color ranges
        mask1 = cv2.inRange(hsv_image, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv_image, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Find contours of red regions
        contours, _ = cv2.findContours(
            red_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        error_indicators = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 5000:  # Adjust as needed
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate red intensity
                red_intensity = np.mean(self.original_image[y:y + h, x:x + w, 2])

                error_indicators.append({
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                    'area': area,
                    'red_intensity': float(red_intensity)
                })

        return error_indicators

    def extract_information(self) -> Dict[str, Any]:
        """
        Comprehensive screenshot information extraction.

        Returns:
            Dictionary with extracted screenshot information
        """
        return {
            'texts': self.extract_text(),
            'buttons': self.detect_buttons(),
            'error_indicators': self.detect_error_indicators(),
            'image_info': {
                'width': self.original_image.shape[1],
                'height': self.original_image.shape[0]
            }
        }


def main():
    """
    Example usage demonstration
    """
    # # Check if image path is provided
    # if len(sys.argv) < 2:
    #     print("Usage: python screenshot_analyzer.py <path_to_screenshot>")
    #     sys.exit(1)
    #
    # # Get screenshot path from command line argument
    # screenshot_path = sys.argv[1]

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/007.png"

    try:
        # Create analyzer instance
        analyzer = ScreenshotAnalyzer(screenshot_path)

        # Extract information
        results = analyzer.extract_information()

        # Pretty print results
        print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"Error processing screenshot: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()