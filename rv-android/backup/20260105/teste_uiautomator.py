#!/usr/bin/python

from uiautomator import Device
import sys




def teste01():
    # get the target device
    d = Device("emulator-5554")
    # d.press

    # dump ui xml
    # d.dump("/home/pedro/tmp/teste_genie/S_1.xml",False,True)
    xml = d.dump()
    print(xml)

    from xml.dom.minidom import parseString,Element, Document
    document: Document
    document = parseString(xml)

    items = []
    dict1 = {"true": True, "false": False}
    node: Element
    for node in document.getElementsByTagName("node"):
        if "br.unb.cic.cryptoapp" == node.getAttribute("package") \
                and "true" == node.getAttribute("visible-to-user") \
                and "true" == node.getAttribute("enabled")\
                and ("true" == node.getAttribute("checkable")
                     or "true" == node.getAttribute("clickable")
                     or "true" == node.getAttribute("scrollable")
                     or "true" == node.getAttribute("long-clickable")):
            print("{} = [id={}, class={}, selected={}]".format(node.getAttribute("text"), node.getAttribute("resource-id"), node.getAttribute("class"), node.getAttribute("selected")))
            item  = {"id": node.getAttribute("resource-id")
                , "text": node.getAttribute("text")
                , "class": node.getAttribute("class").split(".")[-1]
                , "checkable": dict1[node.getAttribute("checkable")]
                , "checked": dict1[node.getAttribute("checked")]
                , "clickable": dict1[node.getAttribute("clickable")]
                , "enabled": dict1[node.getAttribute("enabled")]
                , "focusable": dict1[node.getAttribute("focusable")]
                , "focused": dict1[node.getAttribute("focused")]
                , "scrollable": dict1[node.getAttribute("scrollable")]
                , "long-clickable": dict1[node.getAttribute("clickable")]
                , "password": dict1[node.getAttribute("password")]
                , "selected": dict1[node.getAttribute("selected")]
                , "visible-to-user": dict1[node.getAttribute("visible-to-user")]
                , "bounds": node.getAttribute("bounds")
                }
            items.append(item)
    print(items)

    actions = []
    for item in items:
        if not item["visible-to-user"]:
            continue
        # if item["clickable"]:
        #     actions.add("Click Button '{}' with bounds {}".format(item["text"], item["bounds"]))
        # if item["long-clickable"]:
        #     actions.add("Long click Button '{}' with bounds {}".format(item["text"], item["bounds"]))
        match item:
            case {"class": "Button"} as person:
                print("Processing data for button")
                actions.append("Click Button '{}' with bounds {}".format(item["text"], item["bounds"]))
                # d.click()
            case {"class": "EditText"}:
                print("Processing edit text")
                # compose = set()
                # compose.add("Click EditText '{}' with bounds {}".format(item["text"], item["bounds"]))
                # compose.add("Enter text")
                actions.append(["Click EditText '{}' with bounds {}".format(item["text"], item["bounds"])
                             ,"Enter text"])
            case {"class": "Spinner"}:
                print("Processing spinner")
                actions.append("Click Spinner '{}' with bounds {}".format(item["text"], item["bounds"]))
            case _:
                print("Unknown data format:{}".format(item))
                actions.append("Click BACK")
    for a in actions:
        print(a)
    print("FOI !!!")




if __name__ == '__main__':
    teste01()
