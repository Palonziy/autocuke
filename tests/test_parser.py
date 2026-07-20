import unittest
from pathlib import Path
from app.parser.txt_parser import TXTParser

class TestParser(unittest.TestCase):
    def setUp(self):
        self.mobile_file = Path("scenarios_mobile.txt")
        self.web_file = Path("scenarios_web.txt")

    def test_mobile_parser(self):
        scenarios = TXTParser.parse_file(self.mobile_file)
        self.assertEqual(len(scenarios), 2)
        
        # Test first scenario
        sc1 = scenarios[0]
        self.assertEqual(sc1.name, "Register with valid phone")
        self.assertEqual(sc1.folders, ["Mobile", "Authentication", "Register"])
        self.assertEqual(len(sc1.steps), 3)
        self.assertEqual(sc1.steps[0].action, "Open Registration screen")
        self.assertEqual(sc1.steps[0].result, "Registration screen is displayed")
        self.assertEqual(sc1.steps[2].action, "Tap Continue")
        self.assertEqual(sc1.steps[2].result, "OTP page is displayed")

        # Test second scenario
        sc2 = scenarios[1]
        self.assertEqual(sc2.name, "Register with existing phone")
        self.assertEqual(sc2.folders, ["Mobile", "Authentication", "Register"])
        self.assertEqual(len(sc2.steps), 2)
        self.assertEqual(sc2.steps[1].action, "Enter existing phone number")
        self.assertEqual(sc2.steps[1].result, "Error message 'Phone number already registered' is displayed")

    def test_web_parser(self):
        scenarios = TXTParser.parse_file(self.web_file)
        self.assertEqual(len(scenarios), 1)
        
        sc = scenarios[0]
        self.assertEqual(sc.name, "Add item to cart")
        self.assertEqual(sc.folders, ["Web", "Checkout", "Cart"])
        self.assertEqual(len(sc.steps), 2)
        self.assertEqual(sc.steps[0].action, "Go to Item Details page")
        self.assertEqual(sc.steps[1].action, "Click 'Add to Cart'")
        self.assertEqual(sc.steps[1].result, "Item is successfully added and badge count updates to 1")

if __name__ == "__main__":
    unittest.main()
