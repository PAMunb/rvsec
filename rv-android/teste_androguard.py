from androguard.core.analysis.analysis import Analysis
from androguard.core.bytecodes.apk import APK
from androguard.misc import AnalyzeAPK


# adb shell "dumpsys activity activities | grep mResumedActivity" | awk '{print $4}' | sed 's/\///'
# adb shell "dumpsys window windows | grep -E 'mObscuringWindow'"
# adb shell "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"

def tmp01(apk_path: str):
    a: APK
    d: Analysis

    a, d, dx = AnalyzeAPK(apk_path)

    cg = a.get_call_graph()

    # for method in cg:


def tmp02(apk_path):
    # Open the APK
    a: APK
    d: Analysis

    # a, d, dx = AnalyzeAPK(apk_path)

    a = APK(apk_path)

    r = a.get_android_resources()
    print(r)
    # for s in a.get_android_resources():  # d.get_strings():
    #     print(s)

    # for f in a.get_files():
    #     if "string" in f:
    #       print(f)

    # # Get activities list
    # activities = a.get_activities()
    # print("Activities:")
    # for activity in activities:
    #   print(f"- {activity}")
    #
    #   # Try to link to layout (heuristic approach, might not be accurate)
    #   layout_name = activity.split(".")[-1] + ".xml"  # Basic heuristic based on class name
    #   if layout_name in a.get_files():
    #     print(f"  Possible Layout: {layout_name}")
    #   else:
    #     print(f"  Layout information not found using this approach.")


# Example usage (replace with your APK path)
# analyze_activities_layouts("path/to/your.apk")

if __name__ == '__main__':
    apk = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"
    # tmp01(apk)
    tmp02(apk)
