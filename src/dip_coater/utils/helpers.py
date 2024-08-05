from json import dump, load, JSONDecodeError


def clamp(value, min_value, max_value):
    """Clamp a value between a minimum and maximum value."""
    return max(min(value, max_value), min_value)


def config_save_coder_filepath(app_state, filepath: str):
    data = {'coder_filepath': filepath}
    with open(app_state.config.CONFIG_FILE, "w") as file:
        dump(data, file)


def config_load_coder_filepath(app_state):
    try:
        with open(app_state.config.CONFIG_FILE, "r") as file:
            data = load(file)
            return data.get('coder_filepath')
    except FileNotFoundError:
        return ""
    except JSONDecodeError:        # JSON file is empty or corrupted
        return ""
