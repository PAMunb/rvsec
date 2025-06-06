import os
import os
import sys
from io import StringIO
from unittest.mock import patch, mock_open

import pytest

# Add the parent directory to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rvandroid.domain.classes import Classes, Method
from rvandroid.domain.window import Windows
from rvandroid.parser.static.reach_parser import ReachParser, read_reachable_methods

# Sample CSV data for testing
SAMPLE_CSV_DATA = """class,is_activity,is_main_activity,method,params,reachable,reaches_mop,directly_reaches_mop,signature,mop_methods_reached
br.unb.cic.cryptoapp.MainActivity,true,true,onCreate,"[android.os.Bundle]",true,true,false,"<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>","[]"
br.unb.cic.cryptoapp.MainActivity,true,true,showScreenCipher,"[android.view.View]",true,true,false,"<br.unb.cic.cryptoapp.MainActivity: void showScreenCipher(android.view.View)>","[]"
br.unb.cic.cryptoapp.cipher.CipherUtil,false,false,aes,"[java.lang.String]",true,true,true,"<br.unb.cic.cryptoapp.cipher.CipherUtil: byte[] aes(java.lang.String)>","[<javax.crypto.KeyGenerator: javax.crypto.KeyGenerator getInstance(java.lang.String)>;<javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>]"
br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil,false,false,unreachableHash,"[java.lang.String]",false,false,false,"<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String unreachableHash(java.lang.String)>","[]"
"""


class TestReachParser:
    """Tests for the ReachParser class."""

    @pytest.fixture
    def parser(self):
        """Initialize a ReachParser instance for testing."""
        return ReachParser()

    @pytest.fixture
    def classes(self):
        """Initialize an empty Classes instance for testing."""
        return Classes()

    @pytest.fixture
    def windows(self):
        """Initialize an empty Windows instance for testing."""
        return Windows()

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_CSV_DATA)
    def test_parse_file_success(self, mock_file, mock_exists, parser, classes, windows):
        """Test successful parsing of a reach CSV file."""
        # Setup
        mock_exists.return_value = True

        # Test
        result = parser.parse_file("path/to/reach.csv", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, Classes)
        assert len(result.classes) == 3  # Three unique classes in sample data

        # Check if main activity was correctly identified
        main_activity = result.get_main_activity()
        assert main_activity is not None
        assert main_activity.name == "br.unb.cic.cryptoapp.MainActivity"
        assert main_activity.is_main_activity == True

        # Check method properties
        method = result.methods.get("<br.unb.cic.cryptoapp.cipher.CipherUtil: byte[] aes(java.lang.String)>")
        assert method is not None
        assert method.reaches_mop == True
        assert method.directly_reaches_mop == True

        # Check unreachable method
        method = result.methods.get(
            "<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String unreachableHash(java.lang.String)>")
        assert method is not None
        assert method.reachable == False

    @patch("os.path.exists")
    def test_parse_file_nonexistent(self, mock_exists, parser, classes, windows):
        """Test parsing of a nonexistent CSV file."""
        # Setup
        mock_exists.return_value = False

        # Test
        result = parser.parse_file("path/to/nonexistent.csv", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, Classes)
        assert len(result.classes) == 0  # Should return empty Classes object

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_parse_file_exception(self, mock_file, mock_exists, parser, classes, windows):
        """Test handling of exceptions during parsing."""
        # Setup
        mock_exists.return_value = True
        mock_file.side_effect = Exception("Test exception")

        # Test
        result = parser.parse_file("path/to/reach.csv", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, Classes)
        assert len(result.classes) == 0  # Should return empty Classes object

    def test_read_file(self, parser):
        """Test the read_file method with sample CSV data."""
        # Setup
        csv_file = StringIO(SAMPLE_CSV_DATA)
        with patch("builtins.open", return_value=csv_file):
            # Test
            result = parser.read_file("path/to/reach.csv")

            # Assertions
            assert isinstance(result, Classes)
            assert len(result.classes) == 3

            # Check class details
            assert "br.unb.cic.cryptoapp.MainActivity" in result.classes
            assert "br.unb.cic.cryptoapp.cipher.CipherUtil" in result.classes
            assert "br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil" in result.classes

            # Check method count
            assert len(result.methods) == 4  # Four methods in sample data

    def test_parse_class(self, parser, classes):
        """Test parsing a class from a CSV row."""
        # Setup
        row = ["br.unb.cic.cryptoapp.MainActivity", "true", "true", "onCreate", "[android.os.Bundle]",
               "true", "true", "false", "<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>", "[]"]

        # Test
        class_obj = parser._parse_class(row, classes)

        # Assertions
        assert class_obj.name == "br.unb.cic.cryptoapp.MainActivity"
        assert class_obj.is_activity == True
        assert class_obj.is_main_activity == True
        assert class_obj in classes.classes.values()

    def test_parse_method(self, parser):
        """Test parsing a method from a CSV row."""
        # Setup
        row = ["br.unb.cic.cryptoapp.MainActivity", "true", "true", "onCreate", "[android.os.Bundle]",
               "true", "true", "false", "<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>", "[]"]
        class_name = "br.unb.cic.cryptoapp.MainActivity"

        # Test
        method = parser._parse_method(row, class_name)

        # Assertions
        assert isinstance(method, Method)
        assert method.class_name == "br.unb.cic.cryptoapp.MainActivity"
        assert method.name == "onCreate"
        assert method.params == ["android.os.Bundle"]
        assert method.signature == "<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>"
        assert method.reachable == True
        assert method.reaches_mop == True
        assert method.directly_reaches_mop == False

    def test_parse_params_list(self, parser):
        """Test parsing a parameter list string."""
        # Test various parameter list formats
        assert parser._parse_params_list("[]") == []
        assert parser._parse_params_list("[java.lang.String]") == ["java.lang.String"]
        assert parser._parse_params_list("[java.lang.String;android.os.Bundle]") == ["java.lang.String",
                                                                                     "android.os.Bundle"]
        assert parser._parse_params_list("[byte[];java.lang.String]") == ["byte[]", "java.lang.String"]

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_CSV_DATA)
    def test_read_reachable_methods_function(self, mock_file, mock_exists):
        """Test the read_reachable_methods convenience function."""
        # Setup
        mock_exists.return_value = True

        # Test
        result = read_reachable_methods("path/to/reach.csv")

        # Assertions
        assert isinstance(result, Classes)
        assert len(result.classes) == 3  # Three unique classes in sample data
        assert len(result.methods) == 4  # Four methods in sample data


@patch("os.path.exists")
def test_integration_with_real_data(mock_exists):
    """Test with real data from the provided example."""
    # Setup - use the real CSV data from the example
    real_data = """class,is_activity,is_main_activity,method,params,reachable,reaches_mop,directly_reaches_mop,signature,mop_methods_reached
br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil,false,false,hash,"[byte[];java.lang.String]",true,true,true,"<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String hash(byte[],java.lang.String)>","[<java.security.MessageDigest: void update(byte[])>;<java.security.MessageDigest: byte[] digest()>;<java.security.MessageDigest: java.security.MessageDigest getInstance(java.lang.String)>]"
br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil,false,false,<init>,"[]",true,false,false,"<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: void <init>()>","[]"
br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil,false,false,hash,"[java.lang.String;java.lang.String]",true,true,false,"<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String hash(java.lang.String,java.lang.String)>","[]"
br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil,false,false,unreachableHash,"[java.lang.String]",false,false,false,"<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String unreachableHash(java.lang.String)>","[]"
br.unb.cic.cryptoapp.MainActivity,true,true,onOptionsItemSelected,"[android.view.MenuItem]",false,true,false,"<br.unb.cic.cryptoapp.MainActivity: boolean onOptionsItemSelected(android.view.MenuItem)>","[]"
br.unb.cic.cryptoapp.MainActivity,true,true,<init>,"[]",false,true,false,"<br.unb.cic.cryptoapp.MainActivity: void <init>()>","[]"
br.unb.cic.cryptoapp.MainActivity,true,true,onCreate,"[android.os.Bundle]",true,true,false,"<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>","[]"
br.unb.cic.cryptoapp.cipher.CipherUtil,false,false,aes,"[java.lang.String]",true,true,true,"<br.unb.cic.cryptoapp.cipher.CipherUtil: byte[] aes(java.lang.String)>","[<javax.crypto.KeyGenerator: javax.crypto.KeyGenerator getInstance(java.lang.String)>;<javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>]"
"""

    # Configure os.path.exists to return True for our test file
    mock_exists.return_value = True

    # Mock the open function to return our sample data
    with patch("builtins.open", mock_open(read_data=real_data)):
        # Create the ReachParser instance
        parser = ReachParser()

        # Test
        result = parser.parse_file("path/to/reach.csv", "br.unb.cic.cryptoapp", None, None)

        # Assertions
        assert isinstance(result, Classes)
        assert len(result.classes) > 0

        # Check for specific classes we know should be there
        assert "br.unb.cic.cryptoapp.MainActivity" in result.classes
        assert "br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil" in result.classes
        assert "br.unb.cic.cryptoapp.cipher.CipherUtil" in result.classes

        # Check that MainActivity is correctly marked as main
        main_activity = result.get_main_activity()
        assert main_activity is not None
        assert main_activity.name == "br.unb.cic.cryptoapp.MainActivity"

        # Check counts of different types of methods
        reachable_count = sum(1 for method in result.methods.values() if method.reachable)
        mop_count = sum(1 for method in result.methods.values() if method.reaches_mop)
        direct_mop_count = sum(1 for method in result.methods.values() if method.directly_reaches_mop)

        assert reachable_count > 0
        assert mop_count > 0
        assert direct_mop_count > 0

        # Check a specific method with known properties
        aes_method = result.methods.get("<br.unb.cic.cryptoapp.cipher.CipherUtil: byte[] aes(java.lang.String)>")
        assert aes_method is not None
        assert aes_method.directly_reaches_mop is True
