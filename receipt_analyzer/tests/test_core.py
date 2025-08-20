"""Test basic functionality of core modules."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date

from ..core.config import Config, load_config, save_config
from ..core.logging_utils import Logger, LogRecord, LogStream
from ..core.naming import safe_filename, build_receipt_filename, unique_path
from ..core.parsing import ParsedReceipt, extract_amounts, extract_dates, parse_receipt_text
from ..core.vendors import VendorMap, load_vendor_map, save_vendor_map


class TestConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()
        assert config.detection_method == "opencv"
        assert config.opencv.min_area_ratio == 0.01
        assert config.ocr.language == "eng"
        assert config.output.format == "png"
    
    def test_config_serialization(self):
        """Test configuration save and load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            # Create and save config
            original_config = Config()
            original_config.detection_method = "simple"
            original_config.opencv.min_area_ratio = 0.05
            
            assert save_config(original_config, config_path)
            
            # Load config
            loaded_config = load_config(config_path)
            
            assert loaded_config.detection_method == "simple"
            assert loaded_config.opencv.min_area_ratio == 0.05


class TestLogging:
    """Test logging functionality."""
    
    def test_log_record(self):
        """Test log record creation."""
        record = LogRecord("INFO", "Test message")
        assert record.level == "INFO"
        assert record.message == "Test message"
        assert "Test message" in str(record)
    
    def test_log_stream(self):
        """Test log stream."""
        stream = LogStream()
        
        # Add records
        record1 = LogRecord("INFO", "Message 1")
        record2 = LogRecord("WARN", "Message 2")
        
        stream.add_record(record1)
        stream.add_record(record2)
        
        # Get all records
        all_records = stream.get_records()
        assert len(all_records) == 2
        
        # Get filtered records
        warn_records = stream.get_records("WARN")
        assert len(warn_records) == 1
        assert warn_records[0].level == "WARN"
    
    def test_logger(self):
        """Test logger functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            stream = LogStream()
            
            logger = Logger(log_file, stream)
            logger.info("Test info message")
            logger.warn("Test warning")
            
            # Check stream has records
            records = stream.get_records()
            assert len(records) == 2
            assert records[0].level == "INFO"
            assert records[1].level == "WARN"
            
            # Check file was written
            logger.close()
            assert log_file.exists()
            
            with open(log_file) as f:
                content = f.read()
                assert "Test info message" in content
                assert "Test warning" in content


class TestNaming:
    """Test filename generation and safety."""
    
    def test_safe_filename(self):
        """Test safe filename generation."""
        # Test illegal characters
        assert safe_filename("test<file>name") == "test_file_name"
        assert safe_filename("CON") == "CON_file"  # Reserved name
        assert safe_filename("file.") == "file"  # Trailing dot
        
        # Test normal case
        assert safe_filename("Normal Filename") == "Normal_Filename"
    
    def test_build_receipt_filename(self):
        """Test receipt filename building."""
        receipt = ParsedReceipt()
        receipt.vendor = "Test Vendor"
        receipt.amount = 12.34
        receipt.date = date(2023, 12, 25)
        
        filename = build_receipt_filename(receipt, "png")
        expected = "Test_Vendor_GBP-12-34_25-12-2023.png"
        
        assert filename == expected
    
    def test_unique_path(self):
        """Test unique path generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test.txt"
            
            # First call should return same path
            unique1 = unique_path(base_path)
            assert unique1 == base_path
            
            # Create file, next call should return different path
            base_path.touch()
            unique2 = unique_path(base_path)
            assert unique2 != base_path
            assert "_2" in unique2.stem


class TestParsing:
    """Test text parsing functionality."""
    
    def test_extract_amounts(self):
        """Test amount extraction."""
        text = "Total: £12.34 and also 56.78 GBP plus 1,234.56"
        amounts = extract_amounts(text)
        
        assert len(amounts) >= 2
        amounts_values = [amount for amount, _ in amounts]
        assert 12.34 in amounts_values
        assert 1234.56 in amounts_values
    
    def test_extract_dates(self):
        """Test date extraction."""
        text = "Date: 25/12/2023 or 01-01-2024"
        dates = extract_dates(text)
        
        assert len(dates) >= 2
        date_values = [d for d, _ in dates]
        assert date(2023, 12, 25) in date_values
        assert date(2024, 1, 1) in date_values
    
    def test_parse_receipt_text(self):
        """Test full receipt parsing."""
        text = """
        Tesco Express
        Date: 25/12/2023
        Total: £45.67
        Thank you for shopping with us
        """
        
        parsed = parse_receipt_text(text)
        
        # Should find amount and date
        assert parsed.amount is not None
        assert parsed.date is not None
        assert parsed.amount == 45.67
        assert parsed.date == date(2023, 12, 25)


class TestVendors:
    """Test vendor mapping functionality."""
    
    def test_vendor_map_basic(self):
        """Test basic vendor map operations."""
        vendor_map = VendorMap()
        
        # Add keyword
        vendor_map.add_keyword("test_keyword", "Test Vendor")
        
        # Lookup
        result = vendor_map.lookup_vendor("test_keyword")
        assert result == "Test Vendor"
        
        # Remove
        vendor_map.remove_keyword("test_keyword")
        result = vendor_map.lookup_vendor("test_keyword")
        assert result is None
    
    def test_vendor_map_synonyms(self):
        """Test vendor synonym resolution."""
        vendor_map = VendorMap()
        
        vendor_map.add_synonym("Tesco Stores Ltd", "Tesco")
        
        result = vendor_map.resolve_synonym("Tesco Stores Ltd")
        assert result == "Tesco"
        
        result = vendor_map.resolve_synonym("Unknown Vendor")
        assert result == "Unknown Vendor"
    
    def test_vendor_map_persistence(self):
        """Test vendor map save and load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "vendors.json"
            
            # Create vendor map
            original_map = VendorMap()
            original_map.add_keyword("test", "Test Vendor", is_manual=True)
            
            # Save
            assert save_vendor_map(original_map, map_path)
            
            # Load
            loaded_map = load_vendor_map(map_path)
            
            # Verify
            assert loaded_map.lookup_vendor("test") == "Test Vendor"


if __name__ == "__main__":
    pytest.main([__file__])