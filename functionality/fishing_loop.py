from time import sleep, time
from utils.LastResults import LastResults
from wrappers.logging_wrapper import debug, info
from wrappers.win32api_wrapper import (
    press_key,
    press_mouse_key,
    release_key,
    release_mouse_key,
)
import asyncio
from functionality.fishing_actions import cast, fish_notice, pause, recenter, reel_fish, repairing, select_bait, skipAnimation
from functionality.image_recognition import image_recognition_result


async def fishing_loop(context):
    last_results = LastResults()
    last_repair_time = int(time())
    loop = asyncio.get_event_loop()
    ctx = {
        "loop": loop,
        "config": context.config,
        "consecutive_rods_casted": 0
    }

    while True:
        last_results.add(await call_appropriate_fishing_action(ctx, last_results))
        if ctx["consecutive_rods_casted"] > 8:
            info("Consecutive rods casted more than 8: " + str(ctx["consecutive_rods_casted"]))
            context.destroy()
            break
        if ctx["config"]["repairing"]["enable"].get() == 1:
            should_repair_in = -1 * (int(time()) - last_repair_time - ctx["config"]["repairing"]["every"].get())
            if should_repair_in < 0:
                last_repair_time = int(time())
                info("Repairing")
                await repairing(ctx)
                if ctx["config"]["bait"]["enable"].get() == 1:
                    info("Selecting bait")
                    await select_bait(ctx)


async def call_appropriate_fishing_action(ctx, last_results):

    result_from_model = await image_recognition_result(
        ctx,
        ctx["config"]["fishing"]["x"].get(),
        ctx["config"]["fishing"]["y"].get(),
        ctx["config"]["fishing"]["width"].get(),
        ctx["config"]["fishing"]["height"].get(),
    )

    if (
        last_results.get_last_value() != result_from_model and result_from_model != "1"
    ):  # double checking that it is a correct match
        ctx["consecutive_rods_casted"] = 0
        #info("Resetting rod casts " + str(ctx["consecutive_rods_casted"]))
        return result_from_model
    if (
        last_results.get_last_value() == result_from_model and result_from_model == "5"
    ):
        ctx["consecutive_rods_casted"] = ctx["consecutive_rods_casted"] + 1
        info("Incrementing rod cast " + str(ctx["consecutive_rods_casted"]))
    if result_from_model == "0":  # 0 - model does not match any data (not fish captured yet)
        if last_results.get_one_before_last_value() != "0":
            info("Waiting for fish...")
        return "0"
    elif result_from_model == "1":  # 1 - model noticed a fish(left click to initiate fishing)
        info("Found a fish!")
        await fish_notice(ctx)
        return "1"
    elif result_from_model == "2":  # 2 - model matched the green icon (reeling a fish in)
        if last_results.get_one_before_last_value() != "2":
            info("Green color spotted, Reeling a fish")
            await reel_fish(ctx)
            return "2"
    elif result_from_model == "3":  # 3 - model matched the orange icon (wait x sec)
        if last_results.are_too_much_pauses():
            info("Too much pauses, Reeling a fish!")
            await reel_fish(ctx)
            return "3"
        info("Orange color spotted, Pause fishing")
        await release_mouse_key(ctx)
        await pause(ctx)
        return "3"
    elif result_from_model == "4":  # 4 - model matched the red icon (wait x sec)
        info("Red color spotted, Pause fishing")
        await release_mouse_key(ctx)
        await pause(ctx)
        return "4"
    elif result_from_model == "5":  # 5 - model did not match anything (left click, wait x sec)
        # if last result was green click to remove the animation


        debug("current value: " + result_from_model)
        if last_results.get_last_value():
            debug("last value: " + last_results.get_last_value())
        if last_results.get_one_before_last_value():
            debug("one before: " + last_results.get_one_before_last_value())

        if last_results.get_one_before_last_value() is None or last_results.get_one_before_last_value() == "2" or last_results.get_one_before_last_value() == "3":
            debug("Caught fish clicking mouse to skip animation")
            await release_mouse_key(ctx)
            await pause(ctx)
            await pause(ctx)
            await press_mouse_key(ctx)
            await release_mouse_key(ctx)
            
            await pause(ctx)
            debug("release `")
            await release_key(ctx, "`")
            
            debug("release `")
            await press_key(ctx, "`")
            
        if last_results.get_one_before_last_value() != "0":
            info("Cast fishing rod")
            await cast(ctx)
            return "5"
