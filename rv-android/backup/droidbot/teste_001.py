import argparse
from droidbot import input_manager
from droidbot import input_policy
from droidbot import env_manager
from droidbot import DroidBot
from droidbot.droidmaster import DroidMaster


def main(app_path,
         rvandroid_url="http://localhost:5000/api/get_actions",
         output_dir="/home/pedro/tmp/droidbot-results",
         timeout=600,
         debug=True):
    droidbot = DroidBot(
        app_path=app_path,
        device_serial="emulator-5554",
        is_emulator=True,
        output_dir=output_dir,
        env_policy=env_manager.POLICY_NONE,
        policy_name=input_policy.POLICY_RVANDROID,
        random_input=True,
        # script_path=opts.script_path,
        event_interval=input_manager.DEFAULT_EVENT_INTERVAL,
        timeout=timeout,
        event_count=input_manager.DEFAULT_EVENT_COUNT,
        # cv_mode=opts.cv_mode,
        debug_mode=debug,
        # keep_app=False,
        # keep_env=False,
        # profiling_method=opts.profiling_method,
        grant_perm=True,
        # enable_accessibility_hard=opts.enable_accessibility_hard,
        # master=opts.master,
        # humanoid=opts.humanoid,
        ignore_ad=True,
        # replay_output=opts.replay_output,
        rvandroid_url=rvandroid_url
    )
    droidbot.start()


if __name__ == "__main__":
    apk = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"
    main(apk, timeout=120, debug=False)
