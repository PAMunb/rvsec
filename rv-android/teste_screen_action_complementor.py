# teste_run_server.py
import json
import logging
import os
import sys

from rvandroid.app import App
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.parser.static import static_analysis_parser
from rvandroid.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor

def read_state_file(filename):
    print(f"Lendo arquivo de estado: {filename}")
    with open(filename, 'r') as file:
        return json.load(file)


def tmp_001(screen_description: ScreenDescription, screenshot_path: str):
    complementor = ScreenshotActionComplementor()
    new_screen_description = complementor.complement_screen_actions(screen_description, screenshot_path)
    print(f"Nova descrição da tela:\n{new_screen_description}")
    for key in new_screen_description.keys():
        item = new_screen_description[key]
        print(f"{key} = {item}")


def tmp_002(screen_description: ScreenDescription, screenshot_path: str):
    complementor = ScreenshotActionComplementor()
    result = complementor.complement_screen_actions(screen_description, screenshot_path)

    enhanced_screen = result.get("enhanced_screen")
    visual_mapping = result.get("visual_mapping")

    print(f"Screen Analysis Results:\n")
    print(f"Total UI Elements: {len(screen_description.items)}")
    print(f"Error Indicators: {len(visual_mapping.get('error_indicators', []))}")
    print(f"Visual Buttons: {len(visual_mapping.get('visual_buttons', []))}")
    print(f"Text Elements: {len(visual_mapping.get('text_elements', []))}")
    print(f"Interactive Elements: {len(visual_mapping.get('interactive_elements', []))}")
    print(f"Error Impacted Items: {len(visual_mapping.get('error_impacted_items', []))}")
    print(f"Unmatched Elements: {len(visual_mapping.get('unmatched_elements', []))}\n")

    # Create a list to track item associations instead of using a dictionary
    # This avoids hashability issues with ScreenItem
    item_associations = []

    # Process all UI elements first
    for idx, item in enumerate(screen_description.items):
        item_associations.append({
            'index': idx,
            'item': item,
            'errors': [],
            'buttons': [],
            'texts': [],
            'interactive': []
        })

    # Process error indicators
    for error in visual_mapping.get('error_indicators', []):
        associated_item = error.get('associated_item')
        if associated_item:
            # Find the association entry for this item
            for assoc in item_associations:
                if assoc['item'] is associated_item:  # Direct object comparison
                    assoc['errors'].append(error)
                    break

    # Process visual buttons
    for button in visual_mapping.get('visual_buttons', []):
        associated_item = button.get('associated_item')
        if associated_item:
            # Find the association entry for this item
            for assoc in item_associations:
                if assoc['item'] is associated_item:  # Direct object comparison
                    assoc['buttons'].append(button)
                    break

    # Process text elements
    for text in visual_mapping.get('text_elements', []):
        associated_item = text.get('associated_item')
        if associated_item:
            # Find the association entry for this item
            for assoc in item_associations:
                if assoc['item'] is associated_item:  # Direct object comparison
                    assoc['texts'].append(text)
                    break

    # Process interactive elements
    for elem in visual_mapping.get('interactive_elements', []):
        associated_item = elem.get('associated_item')
        if associated_item:
            # Find the association entry for this item
            for assoc in item_associations:
                if assoc['item'] is associated_item:  # Direct object comparison
                    assoc['interactive'].append(elem)
                    break

    # Print detailed associations for each UI element
    print("UI Elements with Visual Associations:")
    for assoc in item_associations:
        item = assoc['item']

        # Skip items with no visual associations
        if not (assoc['errors'] or assoc['buttons'] or assoc['texts'] or assoc['interactive']):
            continue

        print(f"\nElement {assoc['index']}: {item.base_description}")
        print(f"  Class: {item.view.get('class', 'Unknown')}")

        if item.view.get('text'):
            print(f"  Text: {item.view.get('text')}")

        if item.view.get('resource_id'):
            print(f"  Resource ID: {item.view.get('resource_id')}")

        if assoc['errors']:
            print(f"  Associated Error Indicators ({len(assoc['errors'])}):")
            for error in assoc['errors']:
                print(f"    - Type: {error.get('error_type', 'Unknown')}, Confidence: {error.get('confidence', 0):.2f}")
                if error.get('text'):
                    print(f"      Text: \"{error.get('text')}\"")

        if assoc['buttons']:
            print(f"  Associated Visual Buttons ({len(assoc['buttons'])}):")
            for button in assoc['buttons']:
                print(f"    - Confidence: {button.get('confidence', 0):.2f}")
                if button.get('text'):
                    print(f"      Text: \"{button.get('text')}\"")

        if assoc['texts']:
            print(f"  Associated Text Elements ({len(assoc['texts'])}):")
            for text in assoc['texts']:
                print(f"    - Text: \"{text.get('text', '')}\"")
                print(f"      Confidence: {text.get('confidence', 0):.2f}")

        if assoc['interactive']:
            print(f"  Associated Interactive Elements ({len(assoc['interactive'])}):")
            for elem in assoc['interactive']:
                print(f"    - Type: {elem.get('type', 'Unknown')}, Confidence: {elem.get('confidence', 0):.2f}")

    # Print unmatched elements
    if visual_mapping.get('unmatched_elements'):
        print("\nUnmatched Visual Elements:")
        for elem in visual_mapping.get('unmatched_elements'):
            elem_type = ""
            if "button" in str(elem.get('type', '')).lower() or elem.get('is_button_like', False):
                elem_type = "Button"
            elif "error" in str(elem.get('type', '')).lower():
                elem_type = "Error"
            else:
                elem_type = str(elem.get('type', 'Unknown'))

            print(f"  - Type: {elem_type}, Confidence: {elem.get('confidence', 0):.2f}")
            if elem.get('text'):
                print(f"    Text: \"{elem.get('text')}\"")


def tmp_003(screen_description: ScreenDescription, screenshot_path: str):
    complementor = ScreenshotActionComplementor()
    desc = complementor.complement_screen_actions(screen_description, screenshot_path)
    new_screen_description: ScreenDescription = desc["enhanced_screen"]
    print(f"Nova descrição da tela:\n{new_screen_description}")
    for item in new_screen_description.items:
        print(f"{item}")
        has_error = item.complement.get("has_error")
        print(f"  - has_error = {has_error}")
        if has_error:
            errors = item.complement.get('errors')
            print(f"    - Errors: {len(errors)}")
            for error in errors:
                print(f"    - {error}")
        print(f"  - complement = {item.complement}")


if __name__ == '__main__':
    # Configuração de logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.visitor.base_visitor").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.parser.screen.droidbot.droidbot_parser").setLevel(logging.WARNING)
    logging.getLogger("rvandroid.model.window.Window").setLevel(logging.WARNING)

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "001"
    app_folder = screenshots_folder + "/" + apk
    screenshot_file = os.path.join(app_folder, prefix+".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")
    app = App(os.path.join(app_folder, apk))
    package = app.package_name

    # Carrega análise estática
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    droidbot_state = read_state_file(droidbot_state_file)
    parser = ParserFactory.create(ParserType.DROIDBOT, BasicTextVisitor)
    screen_description = parser.parse(droidbot_state, static_data)
    # print(screen_description)

    # tmp_001(screen_description, screenshot_file)
    # tmp_002(screen_description, screenshot_file)
    tmp_003(screen_description, screenshot_file)
