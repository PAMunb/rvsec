# rvandroid/uiautomator/uiautomator_executor.py

import logging
import json
import os
import subprocess
import time
from typing import Dict, List, Any, Optional

from rvandroid.commands.command import Command
from rvandroid.parser.uiautomator.uiautomator_parser import uiautomator_to_state

logger = logging.getLogger(__name__)

class UIAutomatorExecutor:
    """
    Handles executing UIAutomator commands on the Android device.
    Provides methods to dump screen state and execute actions.
    """
    
    def __init__(self, device_id: str = "emulator-5554"):
        """
        Initialize UIAutomator executor
        
        Args:
            device_id: Device ID to target
        """
        self.device_id = device_id
        self.temp_dir = "/data/local/tmp"
        self.logger = logging.getLogger(__name__)
    
    def dump_ui_hierarchy(self, output_file: Optional[str] = None) -> str:
        """
        Dump the current UI hierarchy using UIAutomator
        
        Args:
            output_file: Optional file to save the XML dump
            
        Returns:
            XML content as string
        """
        self.logger.info("Dumping UI hierarchy with UIAutomator")
        
        # Generate a temporary file if none provided
        if not output_file:
            output_file = f"{self.temp_dir}/ui_dump_{int(time.time())}.xml"
        
        # Execute the UIAutomator dump command
        dump_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'uiautomator dump', 
            output_file
        ])
        result = dump_cmd.invoke()
        
        # Check if the dump was successful
        if "UI hierchary dumped to" not in result.stdout.decode('utf-8', errors='ignore'):
            self.logger.error(f"UIAutomator dump failed: {result.stderr.decode('utf-8', errors='ignore')}")
            return ""
        
        # Read the dump file
        cat_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'cat', 
            output_file
        ])
        result = cat_cmd.invoke()
        
        # Clean up the file
        rm_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'rm', 
            output_file
        ])
        rm_cmd.invoke()
        
        return result.stdout.decode('utf-8', errors='ignore')
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get the current UI state in a format compatible with the system
        
        Returns:
            State dictionary
        """
        xml_content = self.dump_ui_hierarchy()
        if not xml_content:
            return {"error": "Failed to dump UI hierarchy"}
        
        # Convert to state format
        state = uiautomator_to_state(xml_content)
        
        # Enhance with action history if needed
        # state["action_history"] = self._get_action_history()
        
        return state
    
    def execute_action(self, action: Dict[str, Any]) -> bool:
        """
        Execute an action using UIAutomator
        
        Args:
            action: Action dictionary with action_type, target, and params
            
        Returns:
            True if execution was successful, False otherwise
        """
        self.logger.info(f"Executing action: {action}")
        
        action_type = action.get("action_type", "").lower()
        target = action.get("target", "")
        params = action.get("params", {})
        
        if action_type == "click":
            return self._execute_click(target)
        elif action_type == "long_click":
            return self._execute_long_click(target)
        elif action_type == "set_text":
            text = params.get("text", "")
            return self._execute_set_text(target, text)
        elif action_type == "scroll":
            direction = params.get("direction", "down").lower()
            return self._execute_scroll(target, direction)
        elif action_type == "key_event":
            key_code = params.get("key_code", 0)
            return self._execute_key_event(key_code)
        else:
            self.logger.warning(f"Unsupported action type: {action_type}")
            return False
    
    def _execute_click(self, target: str) -> bool:
        """
        Execute a click action
        
        Args:
            target: Resource ID, text, or coordinates for click
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Executing click on target: {target}")
        
        if self._is_coordinates(target):
            # Click on coordinates
            coords = self._parse_coordinates(target)
            if coords:
                x, y = coords
                click_cmd = Command('adb', [
                    '-s', self.device_id, 
                    'shell', 
                    'input', 'tap', str(x), str(y)
                ])
                click_cmd.invoke()
                return True
        else:
            # Dump the current UI state
            xml_content = self.dump_ui_hierarchy()
            
            # First try to find by resource ID
            target_bounds = self._find_element_bounds_by_resource_id(xml_content, target)
            
            # If not found by resource ID, try by text
            if not target_bounds:
                target_bounds = self._find_element_bounds_by_text(xml_content, target)
                
            # If still not found, try by partial resource ID (just the name part)
            if not target_bounds:
                target_bounds = self._find_element_bounds_by_partial_resource_id(xml_content, target)
                
            # If element found by any method, click it
            if target_bounds:
                x = (target_bounds[0][0] + target_bounds[1][0]) // 2
                y = (target_bounds[0][1] + target_bounds[1][1]) // 2
                
                self.logger.info(f"Clicking at coordinates: ({x}, {y})")
                click_cmd = Command('adb', [
                    '-s', self.device_id, 
                    'shell', 
                    'input', 'tap', str(x), str(y)
                ])
                click_cmd.invoke()
                return True
        
        self.logger.error(f"Failed to execute click on target: {target}")
        # TODO executar random???
        return False

    def _find_element_bounds_by_resource_id(self, xml_content: str, resource_id: str) -> Optional[List[List[int]]]:
        """Find element bounds by exact resource ID match"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_content)
            
            # Function to search for the element
            def find_element(element, target_id):
                # Check if this is the element we're looking for
                if 'resource-id' in element.attrib and element.attrib['resource-id'] == target_id:
                    return element
                
                # If not, search children
                for child in element:
                    result = find_element(child, target_id)
                    if result is not None:
                        return result
                
                return None
            
            # Find the element
            element = find_element(root, resource_id)
            if element is not None and 'bounds' in element.attrib:
                bounds_str = element.attrib['bounds']
                return self._parse_bounds_string(bounds_str)
        
        except Exception as e:
            self.logger.error(f"Error finding element by resource ID: {e}")
        
        return None

    def _find_element_bounds_by_text(self, xml_content: str, text: str) -> Optional[List[List[int]]]:
        """Find element bounds by exact text match"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_content)
            
            # Function to search for the element
            def find_element(element, target_text):
                # Check if this is the element we're looking for
                if 'text' in element.attrib and element.attrib['text'] == target_text:
                    return element
                
                # If not, search children
                for child in element:
                    result = find_element(child, target_text)
                    if result is not None:
                        return result
                
                return None
            
            # Find the element
            element = find_element(root, text)
            if element is not None and 'bounds' in element.attrib:
                bounds_str = element.attrib['bounds']
                return self._parse_bounds_string(bounds_str)
        
        except Exception as e:
            self.logger.error(f"Error finding element by text: {e}")
        
        return None

    def _find_element_bounds_by_partial_resource_id(self, xml_content: str, id_part: str) -> Optional[List[List[int]]]:
        """Find element bounds by partial resource ID match (e.g., 'button' matches 'com.example.app:id/button')"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_content)
            
            # Function to search for the element
            def find_element(element, id_part):
                # Check if this is the element we're looking for
                if 'resource-id' in element.attrib and id_part.lower() in element.attrib['resource-id'].lower():
                    return element
                
                # If not, search children
                for child in element:
                    result = find_element(child, id_part)
                    if result is not None:
                        return result
                
                return None
            
            # Find the element
            element = find_element(root, id_part)
            if element is not None and 'bounds' in element.attrib:
                bounds_str = element.attrib['bounds']
                return self._parse_bounds_string(bounds_str)
        
        except Exception as e:
            self.logger.error(f"Error finding element by partial resource ID: {e}")
        
        return None

    def _parse_bounds_string(self, bounds_str: str) -> List[List[int]]:
        """Parse bounds string into a list of coordinates"""
        try:
            # Handle bounds like "[0,0][1080,1920]"
            bounds_parts = bounds_str.replace('[', '').replace(']', '').split(',')
            if len(bounds_parts) == 4:
                return [[int(bounds_parts[0]), int(bounds_parts[1])], 
                        [int(bounds_parts[2]), int(bounds_parts[3])]]
        except Exception as e:
            self.logger.error(f"Error parsing bounds string: {e}")
        
        return [[0, 0], [0, 0]]
    
    def _execute_long_click(self, target: str) -> bool:
        """
        Execute a long click action
        
        Args:
            target: Resource ID or coordinates for long click
            
        Returns:
            True if successful, False otherwise
        """
        if self._is_coordinates(target):
            # Long press on coordinates
            coords = self._parse_coordinates(target)
            if coords:
                x, y = coords
                # Use swipe with same start/end position to simulate long press
                long_press_cmd = Command('adb', [
                    '-s', self.device_id, 
                    'shell', 
                    'input', 'swipe', str(x), str(y), str(x), str(y), '1000'
                ])
                long_press_cmd.invoke()
                return True
        else:
            # Long press on resource ID
            xml_content = self.dump_ui_hierarchy()
            target_bounds = self._find_element_bounds(xml_content, target)
            if target_bounds:
                x = (target_bounds[0][0] + target_bounds[1][0]) // 2
                y = (target_bounds[0][1] + target_bounds[1][1]) // 2
                
                long_press_cmd = Command('adb', [
                    '-s', self.device_id, 
                    'shell', 
                    'input', 'swipe', str(x), str(y), str(x), str(y), '1000'
                ])
                long_press_cmd.invoke()
                return True
        
        self.logger.error(f"Failed to execute long click on target: {target}")
        return False
    
    def _execute_set_text(self, target: str, text: str) -> bool:
        """
        Execute a set text action
        
        Args:
            target: Resource ID of text field
            text: Text to enter
            
        Returns:
            True if successful, False otherwise
        """
        # First click on the field to focus it
        if not self._execute_click(target):
            return False
        
        # Clear existing text
        clear_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'input', 'keyevent', 'KEYCODE_CTRL_A'
        ])
        clear_cmd.invoke()
        
        delete_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'input', 'keyevent', 'KEYCODE_DEL'
        ])
        delete_cmd.invoke()
        
        # Input the new text
        text_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            f'input text "{text}"'
        ])
        text_cmd.invoke()
        
        return True
    
    def _execute_scroll(self, target: str, direction: str) -> bool:
        """
        Execute a scroll action
        
        Args:
            target: Resource ID of scrollable element
            direction: Direction to scroll (up, down, left, right)
            
        Returns:
            True if successful, False otherwise
        """
        xml_content = self.dump_ui_hierarchy()
        target_bounds = self._find_element_bounds(xml_content, target)
        
        if not target_bounds:
            self.logger.error(f"Failed to find scrollable element: {target}")
            return False
        
        # Calculate scroll coordinates
        x1 = (target_bounds[0][0] + target_bounds[1][0]) // 2
        y1 = (target_bounds[0][1] + target_bounds[1][1]) // 2
        x2 = x1
        y2 = y1
        
        # Adjust end coordinates based on direction
        if direction == "up":
            y2 = y1 + 300
        elif direction == "down":
            y2 = y1 - 300
        elif direction == "left":
            x2 = x1 + 300
        elif direction == "right":
            x2 = x1 - 300
        
        # Execute the scroll
        scroll_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'input', 'swipe', 
            str(x1), str(y1), str(x2), str(y2)
        ])
        scroll_cmd.invoke()
        
        return True
    
    def _execute_key_event(self, key_code: int) -> bool:
        """
        Execute a key event
        
        Args:
            key_code: Android key code
            
        Returns:
            True if successful, False otherwise
        """
        key_cmd = Command('adb', [
            '-s', self.device_id, 
            'shell', 
            'input', 'keyevent', str(key_code)
        ])
        key_cmd.invoke()
        
        return True
    
    def _is_coordinates(self, target: str) -> bool:
        """Check if target is coordinates like '100,200'"""
        if not target:
            return False
        
        parts = target.split(',')
        if len(parts) != 2:
            return False
        
        try:
            x, y = int(parts[0]), int(parts[1])
            return True
        except ValueError:
            return False
    
    def _parse_coordinates(self, target: str) -> Optional[List[int]]:
        """Parse coordinates from string like '100,200'"""
        try:
            x, y = map(int, target.split(','))
            return [x, y]
        except (ValueError, AttributeError):
            return None
    
    def _find_element_bounds(self, xml_content: str, resource_id: str) -> Optional[List[List[int]]]:
        """
        Find the bounds of an element by its resource ID
        
        Args:
            xml_content: XML dump content
            resource_id: Resource ID to look for
            
        Returns:
            Bounds as [[x1, y1], [x2, y2]] or None if not found
        """
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_content)
            
            # Function to search for the element
            def find_element_with_resource_id(element, target_id):
                # Check if this is the element we're looking for
                if 'resource-id' in element.attrib:
                    if element.attrib['resource-id'].endswith('/' + target_id) or element.attrib['resource-id'] == target_id:
                        return element
                
                # If not, search children
                for child in element:
                    result = find_element_with_resource_id(child, target_id)
                    if result is not None:
                        return result
                
                return None
            
            # Find the element
            element = find_element_with_resource_id(root, resource_id)
            if element is not None and 'bounds' in element.attrib:
                bounds_str = element.attrib['bounds']
                # Parse bounds like "[0,0][1080,1920]"
                bounds_parts = bounds_str.replace('[', '').replace(']', '').split(',')
                if len(bounds_parts) == 4:
                    return [[int(bounds_parts[0]), int(bounds_parts[1])], 
                            [int(bounds_parts[2]), int(bounds_parts[3])]]
        
        except Exception as e:
            self.logger.error(f"Error finding element bounds: {e}")
        
        return None