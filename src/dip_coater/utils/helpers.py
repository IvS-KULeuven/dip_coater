from json import dump, load, JSONDecodeError


def clamp(value, min_value, max_value):
    """Clamp a value between a minimum and maximum value.

    :param value: Value to constrain.
    :param min_value: Minimum allowed value.
    :param max_value: Maximum allowed value.
    :return: ``value`` constrained to the inclusive range.
    """
    return max(min(value, max_value), min_value)


def config_save_coder_filepath(app_state, filepath: str):
    """Save the current coder script path to the app config file.

    :param app_state: Application state that provides the config-file path.
    :param filepath: Coder script path to store.
    """
    data = {"coder_filepath": filepath}
    with open(app_state.config.CONFIG_FILE, "w") as file:
        dump(data, file)


def config_load_coder_filepath(app_state):
    """Load the current coder script path from the app config file.

    :param app_state: Application state that provides the config-file path.
    :return: Stored coder script path, or an empty string when unavailable.
    """
    try:
        with open(app_state.config.CONFIG_FILE, "r") as file:
            data = load(file)
            return data.get("coder_filepath")
    except FileNotFoundError:
        return ""
    except JSONDecodeError:  # JSON file is empty or corrupted
        return ""
