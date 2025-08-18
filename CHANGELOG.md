# Receipt Analyzer Changelog

## Unreleased

### Stability
- Added robust error handling in OpenCV detection to prevent crashes with degenerate contours
- Added fallback to whole page when OpenCV detection fails to find valid receipts
- Fixed issues with perspective transformation on invalid quadrilaterals
- Added validation for image dimensions before saving to prevent zero-sized image crashes
- Improved OCR handling for small images and added orientation detection safeguards
- Enhanced PDF rasterization with better error handling and timeouts for missing Poppler
- Added placeholder values for missing vendor, date, and amount data
- Fixed GUI thread safety issues by properly marshaling UI updates to the main thread
- Added detailed debug logging for OpenCV contour detection and processing
- Improved error logging for both CLI and GUI modes

### Tests
- Added regression tests for handling degenerate OpenCV contours
- Added tests for OCR with very small images and null inputs
- Added tests for handling Unicode paths and Windows reserved filenames
- Added tests for robust Poppler fallback and PDF rasterization
