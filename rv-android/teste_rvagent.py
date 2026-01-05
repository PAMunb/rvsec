import logging
import os
import sys
from datetime import datetime
from typing import Optional

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


def execute(config: RVAgentConfig, static_data: Optional[StaticAnalysisData]):
    try:
        agent = AgentFactory.create_agent(config, static_data)
        result = agent.run()

        print(result)
    except Exception as e:
        print(f"❌ Test failed for {package}: {e}")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger("androguard").setLevel(logging.WARNING)

    logging.info("Starting...")

    apk = "cryptoapp.apk"
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"

    app_folder = os.path.join(screenshots_folder, apk)
    apk_path = os.path.join(app_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")

    print(f"📂 Test files:")
    print(f"  • APK: {apk}")

    # Get package name using App class
    app = App(app_path=apk_path)
    package = app.package_name
    print(f"  • Package: {package}")

    print("\n📊 Parsing static analysis data...")
    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.parse(reach_file, gator_file, gesda_file, package)
    print(f"  ✅ Static data parsed")

    config = RVAgentConfig(
        package_name=package,
        # agent_mode="multimode",
        strategy="dfs",
        llm_probability=0.7,
        llm_model="qwen3-vl-4b-8k:latest",
        # llm_temperature=0.25,
        prompt_version="v12",
        timeout=60,
        screenshot_dir=f"/tmp/test_rvagent_{datetime.now().strftime('%Y%m%d_%H%M%S')}/{package}",
        screenshot_rotation_limit=10
    )

    execute(config, static_data)
